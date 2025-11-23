from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.media import Media, MediaStatus, MediaType
from app.models.video import UploadChunk  # Keep for chunk tracking
from app.services.video_processor import VideoProcessor
from app.services.storage import StorageService
from app.workers.tasks import process_video_task
from app.config import get_settings
from datetime import datetime
from pathlib import Path
import magic
import uuid
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
    """List all media with pagination (unified schema)"""
    query = db.query(Media).filter(Media.deleted_at.is_(None))
    
    if status:
        query = query.filter(Media.status == status)
    
    total = query.count()
    media_list = query.order_by(Media.created_at.desc()).offset(skip).limit(limit).all()
    
    # Build response with thumbnails from assets
    video_list = []
    for m in media_list:
        # Get first thumbnail from assets
        thumbnail = None
        for asset in m.assets:
            if asset.asset_type.value == "thumbnail" and asset.status == "ready":
                relative_path = Path(asset.file_path).relative_to(settings.BASE_STORAGE_PATH)
                thumbnail = f"/storage/{relative_path}"
                break
        
        video_list.append({
            "id": m.video_id,  # Use video_id as the identifier
            "title": m.title,
            "filename": m.original_filename or m.filename,
            "status": m.status,
            "duration": m.duration_seconds,
            "created_at": m.created_at,
            "thumbnail": thumbnail
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "videos": video_list
    }

@router.post("/")
@router.post("/upload")  # Alias for convenience
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
        
        # Create media record WITH original_path (unified schema)
        media = Media(
            video_id=video_id,
            filename=file.filename,
            original_filename=file.filename,
            file_extension=file_ext,
            mime_type=mime_type,
            media_type=MediaType.VIDEO.value,
            status=MediaStatus.UPLOAD_COMPLETE.value,
            title=title or file.filename,
            description=description,
            file_size=file_size,
            original_path=final_path,
            checksum_md5=VideoProcessor.calculate_md5(final_path),
            upload_completed_at=datetime.utcnow().isoformat()
        )
        db.add(media)
        db.commit()
        
        # Trigger processing
        process_video_task.delay(video_id)
        
        logger.info(f"Media uploaded: {video_id} ({media.file_size} bytes)")
        
        return {
            "video_id": video_id,
            "filename": media.original_filename,
            "status": media.status,
            "file_size": media.file_size,
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
        # Get or create media record
        media = db.query(Media).filter(Media.video_id == video_id).first()
        
        if not media:
            # First chunk - create media record
            media = Media(
                video_id=video_id,
                filename=filename,
                original_filename=filename,
                file_extension=Path(filename).suffix.lower(),
                media_type=MediaType.VIDEO.value,
                status=MediaStatus.UPLOADING.value,
                file_size=0  # Will be updated when complete
            )
            db.add(media)
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
                    media.filename
                )
                
                media.original_path = final_path
                media.file_size = Path(final_path).stat().st_size
                media.checksum_md5 = VideoProcessor.calculate_md5(final_path)
                media.status = MediaStatus.UPLOAD_COMPLETE.value
                media.upload_completed_at = datetime.utcnow().isoformat()
                db.commit()
                
                # Trigger processing
                process_video_task.delay(video_id)
                
                return {
                    "video_id": video_id,
                    "status": "complete",
                    "message": "All chunks received. Processing started."
                }
                
            except Exception as e:
                media.status = MediaStatus.FAILED.value
                media.error_message = f"Chunk assembly failed: {str(e)}"
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
    """Get media details and all assets (unified schema)"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get all assets
    assets = {}
    for asset in media.assets:
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
        for asset in media.assets 
        if asset.asset_type.value == "thumbnail" and asset.status == "ready"
    ]
    
    return {
        "id": media.video_id,  # Use video_id as identifier
        "title": media.title,
        "description": media.description,
        "filename": media.original_filename or media.filename,
        "status": media.status,
        "file_size": media.file_size,
        "duration": media.duration_seconds,
        "duration_seconds": media.duration_seconds,
        "width": media.width,
        "height": media.height,
        "resolution": f"{media.width}x{media.height}" if media.width else None,
        "fps": media.fps,
        "aspect_ratio": media.aspect_ratio,
        "has_audio": media.has_audio,
        "codec": media.video_codec,
        "video_codec": media.video_codec,
        "audio_codec": media.audio_codec,
        "created_at": media.created_at,
        "processing_started_at": media.processing_started_at,
        "processing_completed_at": media.processing_completed_at,
        "assets": assets,
        "thumbnails": thumbnails,
        "error": media.error_message,
        "analysis_metadata": media.analysis_metadata,  # Include analysis metadata
        "original_path": media.original_path,
        "thumbnail": thumbnails[0] if thumbnails else None
    }

@router.get("/{video_id}/logs")
async def get_processing_logs(video_id: str, db: Session = Depends(get_db)):
    """Get processing logs for debugging"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    logs = [
        {
            "step": log.step,
            "level": log.level,  # Use 'level' instead of 'status' (matches unified schema)
            "message": log.message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "error": log.error_details
        }
        for log in media.processing_logs
    ]
    
    return {"video_id": video_id, "logs": logs}

@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Soft delete media"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    media.deleted_at = datetime.utcnow().isoformat()
    media.status = MediaStatus.ARCHIVED.value
    db.commit()
    
    # Optionally, physically delete files
    # StorageService.delete_video(video_id)
    
    return {"message": "Media deleted successfully"}