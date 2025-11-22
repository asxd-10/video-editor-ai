from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.video import Video, VideoStatus, UploadChunk
from app.services.video_processor import VideoProcessor
from app.services.storage import StorageService
from app.workers.tasks import process_video_task
from app.config import get_settings
from datetime import datetime
from pathlib import Path
import magic
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

@router.get("/")
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all videos with pagination"""
    query = db.query(Video).filter(Video.deleted_at.is_(None))
    
    if status:
        query = query.filter(Video.status == status)
    
    total = query.count()
    videos = query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
    
    # Build response with thumbnails from assets
    video_list = []
    for v in videos:
        # Get first thumbnail from assets
        thumbnail = None
        for asset in v.assets:
            if asset.asset_type.value == "thumbnail" and asset.status == "ready":
                relative_path = Path(asset.file_path).relative_to(settings.BASE_STORAGE_PATH)
                thumbnail = f"/storage/{relative_path}"
                break
        
        video_list.append({
            "id": v.id,
            "title": v.title,
            "filename": v.original_filename,
            "status": v.status.value,  # Convert enum to string
            "duration": v.duration_seconds,
            "created_at": v.created_at,
            "thumbnail": thumbnail
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "videos": video_list
    }

@router.post("/")
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a single video file (for smaller files)
    """
    try:
        # Generate video ID
        video_id = str(uuid.uuid4())
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed: {settings.ALLOWED_VIDEO_EXTENSIONS}"
            )
        
        # Check MIME type
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type not allowed: {mime_type}"
            )
        
        # Save file FIRST (before creating DB record)
        final_path = StorageService.save_upload(
            file.file,
            video_id,
            file.filename
        )
        
        # Get file size
        file_size = Path(final_path).stat().st_size
        
        # Create video record WITH original_path
        video = Video(
            id=video_id,
            filename=file.filename,
            original_filename=file.filename,
            file_extension=file_ext,
            mime_type=mime_type,
            status=VideoStatus.UPLOAD_COMPLETE,
            title=title or file.filename,
            description=description,
            file_size=file_size,
            original_path=final_path,
            checksum_md5=VideoProcessor.calculate_md5(final_path),
            upload_completed_at=datetime.utcnow().isoformat()
        )
        db.add(video)
        db.commit()
        
        # Trigger processing
        process_video_task.delay(video_id)
        
        logger.info(f"Video uploaded: {video_id} ({video.file_size} bytes)")
        
        return {
            "video_id": video_id,
            "filename": video.original_filename,
            "status": video.status.value,
            "file_size": video.file_size,
            "message": "Upload complete. Processing started."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Clean up file if it was saved but DB insert failed
        try:
            if 'final_path' in locals() and Path(final_path).exists():
                Path(final_path).unlink()
                # Also try to remove the directory if empty
                video_dir = Path(final_path).parent
                if video_dir.exists() and not any(video_dir.iterdir()):
                    video_dir.rmdir()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chunk")
async def upload_chunk(
    video_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload video in chunks (for large files)
    """
    try:
        # Get or create video record
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            # First chunk - create video record
            video = Video(
                id=video_id,
                filename=filename,
                original_filename=filename,
                file_extension=Path(filename).suffix.lower(),
                status=VideoStatus.UPLOADING,
                file_size=0  # Will be updated when complete
            )
            db.add(video)
            db.commit()
        
        # Read chunk
        chunk_data = await file.read()
        
        # Save chunk
        chunk_path = StorageService.save_chunk(chunk_data, video_id, chunk_number)
        
        # Record chunk
        chunk_record = UploadChunk(
            video_id=video_id,
            chunk_number=chunk_number,
            chunk_size=len(chunk_data),
            checksum=VideoProcessor.calculate_md5(chunk_path)
        )
        db.add(chunk_record)
        db.commit()
        
        logger.info(f"Chunk {chunk_number}/{total_chunks} saved for {video_id}")
        
        # Check if all chunks received
        uploaded_chunks = db.query(UploadChunk).filter(
            UploadChunk.video_id == video_id
        ).count()
        
        if uploaded_chunks == total_chunks:
            # Assemble chunks
            logger.info(f"All chunks received for {video_id}. Assembling...")
            
            try:
                final_path = StorageService.assemble_chunks(
                    video_id, 
                    total_chunks,
                    video.filename
                )
                
                video.original_path = final_path
                video.file_size = Path(final_path).stat().st_size
                video.checksum_md5 = VideoProcessor.calculate_md5(final_path)
                video.status = VideoStatus.UPLOAD_COMPLETE
                video.upload_completed_at = datetime.utcnow().isoformat()
                db.commit()
                
                # Trigger processing
                process_video_task.delay(video_id)
                
                return {
                    "video_id": video_id,
                    "status": "complete",
                    "message": "All chunks received. Processing started."
                }
                
            except Exception as e:
                video.status = VideoStatus.FAILED
                video.error_message = f"Chunk assembly failed: {str(e)}"
                db.commit()
                raise HTTPException(status_code=500, detail=str(e))
        
        return {
            "video_id": video_id,
            "chunk_number": chunk_number,
            "total_chunks": total_chunks,
            "uploaded_chunks": uploaded_chunks,
            "status": "in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chunk upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}")
async def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get video details and all assets"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get all assets
    assets = {}
    for asset in video.assets:
        if asset.status == "ready":
            # Convert absolute path to URL path
            relative_path = Path(asset.file_path).relative_to(settings.BASE_STORAGE_PATH)
            assets[asset.asset_type.value] = {
                "url": f"/storage/{relative_path}",
                "width": asset.width,
                "height": asset.height,
                "file_size": asset.file_size
            }
    
    # Get thumbnails
    thumbnails = [
        f"/storage/{Path(asset.file_path).relative_to(settings.BASE_STORAGE_PATH)}"
        for asset in video.assets 
        if asset.asset_type.value == "thumbnail" and asset.status == "ready"
    ]
    
    return {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "filename": video.original_filename,
        "status": video.status,
        "file_size": video.file_size,
        "duration": video.duration_seconds,
        "resolution": f"{video.width}x{video.height}" if video.width else None,
        "fps": video.fps,
        "aspect_ratio": video.aspect_ratio,
        "has_audio": video.has_audio,
        "codec": video.video_codec,
        "created_at": video.created_at,
        "processing_started_at": video.processing_started_at,
        "processing_completed_at": video.processing_completed_at,
        "assets": assets,
        "thumbnails": thumbnails,
        "error": video.error_message
    }

@router.get("/{video_id}/logs")
async def get_processing_logs(video_id: str, db: Session = Depends(get_db)):
    """Get processing logs for debugging"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    logs = [
        {
            "step": log.step,
            "status": log.status,
            "message": log.message,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
            "error": log.error_details
        }
        for log in video.processing_logs
    ]
    
    return {"video_id": video_id, "logs": logs}

@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Soft delete a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video.deleted_at = datetime.utcnow().isoformat()
    video.status = VideoStatus.ARCHIVED
    db.commit()
    
    # Optionally, physically delete files
    # StorageService.delete_video(video_id)
    
    return {"message": "Video deleted successfully"}