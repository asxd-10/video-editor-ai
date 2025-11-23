from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.video import Video, VideoAsset, ProcessingLog, VideoStatus, VideoQuality
from app.models.edit_job import EditJob, EditJobStatus
from app.services.video_processor import VideoProcessor
from app.services.storage import StorageService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def log_processing_step(db, video_id: str, step: str, status: str, message: str = None, error: dict = None):
    """Helper to log processing steps"""
    log = ProcessingLog(
        video_id=video_id,
        step=step,
        status=status,
        message=message,
        error_details=error,
        started_at=datetime.utcnow().isoformat()
    )
    db.add(log)
    db.commit()

@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, video_id: str):
    """
    Complete video processing pipeline:
    1. Validate video
    2. Extract metadata
    3. Create proxy
    4. Generate thumbnails
    """
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return
        
        logger.info(f"Starting processing for video {video_id}")
        video.status = VideoStatus.PROCESSING
        video.processing_started_at = start_time.isoformat()
        db.commit()
        
        # Step 1: Validate
        log_processing_step(db, video_id, "validate", "started")
        try:
            VideoProcessor.validate_video(video.original_path)
            log_processing_step(db, video_id, "validate", "completed", "Video file is valid")
        except Exception as e:
            log_processing_step(db, video_id, "validate", "failed", str(e))
            raise
        
        # Step 2: Extract metadata
        log_processing_step(db, video_id, "extract_metadata", "started")
        try:
            metadata = VideoProcessor.extract_metadata(video.original_path)
            
            # Update video with metadata
            video.duration_seconds = metadata['duration']
            video.fps = metadata['fps']
            video.width = metadata['width']
            video.height = metadata['height']
            video.video_codec = metadata['video_codec']
            video.audio_codec = metadata['audio_codec']
            video.bitrate_kbps = metadata['bitrate']
            video.has_audio = metadata['has_audio']
            video.aspect_ratio = metadata['aspect_ratio']
            db.commit()
            
            log_processing_step(db, video_id, "extract_metadata", "completed", 
                              f"Duration: {metadata['duration']}s, Resolution: {metadata['width']}x{metadata['height']}")
        except Exception as e:
            log_processing_step(db, video_id, "extract_metadata", "failed", str(e))
            raise
        
        # Step 3: Create proxy
        log_processing_step(db, video_id, "create_proxy", "started")
        try:
            processed_dir = StorageService.get_processed_directory(video_id)
            proxy_path = processed_dir / "proxy.mp4"
            
            proxy_metadata = VideoProcessor.create_proxy(
                video.original_path,
                str(proxy_path)
            )
            
            # Create VideoAsset record
            proxy_asset = VideoAsset(
                video_id=video_id,
                asset_type=VideoQuality.PROXY_720P,
                file_path=str(proxy_path),
                file_size=proxy_metadata['file_size'],
                width=proxy_metadata['width'],
                height=proxy_metadata['height'],
                duration_seconds=proxy_metadata['duration'],
                status="ready"
            )
            db.add(proxy_asset)
            db.commit()
            
            log_processing_step(db, video_id, "create_proxy", "completed",
                              f"Proxy created: {proxy_metadata['width']}x{proxy_metadata['height']}")
        except Exception as e:
            log_processing_step(db, video_id, "create_proxy", "failed", str(e))
            # Don't fail entire job if proxy fails
            logger.warning(f"Proxy creation failed but continuing: {e}")
        
        # Step 4: Generate thumbnails
        log_processing_step(db, video_id, "generate_thumbnails", "started")
        try:
            thumb_dir = StorageService.get_processed_directory(video_id) / "thumbnails"
            thumbnails = VideoProcessor.extract_thumbnails(
                video.original_path,
                str(thumb_dir),
                count=5
            )
            
            for thumb_path in thumbnails:
                thumb_asset = VideoAsset(
                    video_id=video_id,
                    asset_type=VideoQuality.THUMBNAIL,
                    file_path=thumb_path,
                    file_size=os.path.getsize(thumb_path),
                    status="ready"
                )
                db.add(thumb_asset)
            db.commit()
            
            log_processing_step(db, video_id, "generate_thumbnails", "completed",
                              f"{len(thumbnails)} thumbnails created")
        except Exception as e:
            log_processing_step(db, video_id, "generate_thumbnails", "failed", str(e))
            logger.warning(f"Thumbnail generation failed but continuing: {e}")
        
        # Mark as complete
        video.status = VideoStatus.READY
        video.processing_completed_at = datetime.utcnow().isoformat()
        db.commit()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Processing completed for {video_id} in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Processing failed for {video_id}: {str(e)}")
        video.status = VideoStatus.FAILED
        video.error_message = str(e)
        db.commit()
        
        # Retry logic
        try:
            self.retry(exc=e, countdown=60)  # Retry after 1 minute
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {video_id}")
    
    finally:
        db.close()

import os

@celery_app.task(bind=True, max_retries=3)
def transcribe_video_task(self, video_id: str):
    """Transcribe video using Whisper"""
    from app.services.transcription_service import TranscriptionService
    
    try:
        service = TranscriptionService()
        result = service.transcribe_video(video_id)
        logger.info(f"Transcription task completed for {video_id}")
        return result
    except Exception as e:
        logger.error(f"Transcription task failed for {video_id}: {e}")
        raise self.retry(exc=e, countdown=60)

@celery_app.task(bind=True, max_retries=3)
def analyze_video_task(self, video_id: str):
    """Analyze video: silence detection + scene detection"""
    from app.services.analysis_service import AnalysisService
    from app.services.transcription_service import TranscriptionService
    from pathlib import Path
    
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        # Get audio path (extract if needed)
        transcription_service = TranscriptionService()
        audio_path = transcription_service._extract_audio(video.original_path, video_id)
        
        # Run analysis
        analysis_service = AnalysisService()
        result = analysis_service.analyze_video(
            video_id,
            video.original_path,
            str(audio_path)
        )
        
        # Store in video.analysis_metadata
        video.analysis_metadata = result
        db.commit()
        
        logger.info(f"Analysis task completed for {video_id}")
        return result
    except Exception as e:
        logger.error(f"Analysis task failed for {video_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def create_edit_job_task(self, job_id: str):
    """
    Process an edit job: apply edits and render video.
    
    Args:
        job_id: EditJob ID
    """
    from app.services.editor import EditorService
    
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        # Load edit job
        edit_job = db.query(EditJob).filter(EditJob.id == job_id).first()
        if not edit_job:
            logger.error(f"EditJob {job_id} not found")
            return
        
        logger.info(f"Starting edit job {job_id} for video {edit_job.video_id}")
        
        # Update status
        edit_job.status = EditJobStatus.PROCESSING
        edit_job.started_at = start_time.isoformat()
        db.commit()
        
        # Create editor service
        editor = EditorService()
        
        # Apply edits
        result = editor.create_edit(
            video_id=edit_job.video_id,
            clip_candidate_id=edit_job.clip_candidate_id,
            edit_options=edit_job.edit_options
        )
        
        # Update job with output paths
        edit_job.output_paths = result["output_paths"]
        edit_job.status = EditJobStatus.COMPLETED
        edit_job.completed_at = datetime.utcnow().isoformat()
        db.commit()
        
        logger.info(f"Edit job {job_id} completed successfully")
        return {
            "job_id": job_id,
            "output_paths": result["output_paths"]
        }
        
    except Exception as e:
        logger.error(f"Edit job {job_id} failed: {e}")
        
        # Update job status
        try:
            edit_job = db.query(EditJob).filter(EditJob.id == job_id).first()
            if edit_job:
                edit_job.status = EditJobStatus.FAILED
                edit_job.error_message = str(e)[:500]  # Truncate to 500 chars
                edit_job.completed_at = datetime.utcnow().isoformat()
                db.commit()
        except:
            pass
        
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()