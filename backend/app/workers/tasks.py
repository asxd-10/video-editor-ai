from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.media import Media, MediaStatus, MediaType
from app.models.video import VideoAsset, ProcessingLog, VideoQuality  # Keep VideoAsset for now
from app.models.edit_job import EditJob, EditJobStatus
from app.models.ai_edit_job import AIEditJob, AIEditJobStatus
from app.services.video_processor import VideoProcessor
from app.services.storage import StorageService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def log_processing_step(db, video_id: str, step: str, status: str, message: str = None, error: dict = None):
    """Helper to log processing steps"""
    # Map status to level (unified schema uses 'level' instead of 'status')
    level_map = {
        'started': 'INFO',
        'completed': 'INFO',
        'failed': 'ERROR'
    }
    level = level_map.get(status, 'INFO')
    
    log = ProcessingLog(
        video_id=video_id,
        step=step,
        level=level,
        message=message or f"{step}: {status}",
        error_details=error
        # created_at will be set by server_default
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
        media = db.query(Media).filter(Media.video_id == video_id).first()
        if not media:
            logger.error(f"Media {video_id} not found")
            return
        
        logger.info(f"Starting processing for media {video_id}")
        media.status = MediaStatus.PROCESSING.value
        media.processing_started_at = start_time.isoformat()
        db.commit()
        
        # Step 1: Validate
        log_processing_step(db, video_id, "validate", "started")
        try:
            VideoProcessor.validate_video(media.original_path)
            log_processing_step(db, video_id, "validate", "completed", "Video file is valid")
        except Exception as e:
            log_processing_step(db, video_id, "validate", "failed", str(e))
            raise
        
        # Step 2: Extract metadata
        log_processing_step(db, video_id, "extract_metadata", "started")
        try:
            metadata = VideoProcessor.extract_metadata(media.original_path)
            
            # Update media with metadata
            media.duration_seconds = metadata['duration']
            media.fps = metadata['fps']
            media.width = metadata['width']
            media.height = metadata['height']
            media.video_codec = metadata['video_codec']
            media.audio_codec = metadata['audio_codec']
            media.bitrate_kbps = metadata['bitrate']
            media.has_audio = metadata['has_audio']
            media.aspect_ratio = metadata['aspect_ratio']
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
                media.original_path,
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
                media.original_path,
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
        media.status = MediaStatus.READY.value
        media.processing_completed_at = datetime.utcnow().isoformat()
        db.commit()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Processing completed for {video_id} in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Processing failed for {video_id}: {str(e)}")
        media = db.query(Media).filter(Media.video_id == video_id).first()
        if media:
            media.status = MediaStatus.FAILED.value
            media.error_message = str(e)
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


@celery_app.task(bind=True, max_retries=3)
def apply_ai_edit_task(self, edit_job_id: str):
    """
    Apply AI edit plan (render video from EDL).
    Background task for non-blocking video rendering.
    
    Args:
        edit_job_id: EditJob ID (contains EDL in edit_options)
    """
    from app.services.editor import EditorService
    
    db = SessionLocal()
    edit_job = None
    try:
        edit_job = db.query(EditJob).filter(EditJob.id == edit_job_id).first()
        if not edit_job:
            logger.error(f"EditJob {edit_job_id} not found")
            return
        
        logger.info(f"Starting AI edit rendering for EditJob {edit_job_id}")
        
        # Update status
        edit_job.status = EditJobStatus.PROCESSING
        edit_job.started_at = datetime.utcnow()
        db.commit()
        
        # Extract EDL and cached media data from edit_options
        edit_options = edit_job.edit_options or {}
        ai_edl = edit_options.pop("_ai_edl", [])
        ai_edit_job_id = edit_options.pop("_ai_edit_job_id", None)
        cached_media_data = edit_options.pop("_media_data", None)  # Cached to avoid DB query
        
        if not ai_edl:
            raise ValueError("No EDL found in edit_options")
        
        # Download and cache video file if it's a URL (S3 or HTTP)
        # This avoids network issues during rendering and database connection timeouts
        if cached_media_data:
            video_url = cached_media_data.get("video_url")
            original_path = cached_media_data.get("original_path")
            
            # Determine if we need to download (if video_url is a URL)
            cached_video_path = None
            if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
                # Download and cache the video file
                logger.info(f"Downloading video from URL for caching: {video_url[:80]}...")
                from app.services.storage import StorageService
                try:
                    cached_video_path = StorageService.download_video_from_url(
                        video_url, 
                        edit_job.video_id
                    )
                    # Update cached_media_data to use the local cached file
                    cached_media_data["cached_video_path"] = cached_video_path
                    logger.info(f"Video cached locally: {cached_video_path}")
                except Exception as e:
                    logger.warning(f"Failed to download video from URL, will try direct URL access: {e}")
                    # Continue with URL - FFmpeg might still be able to handle it
            elif original_path and (original_path.startswith('http://') or original_path.startswith('https://')):
                # Fallback: original_path is a URL
                logger.info(f"Downloading video from original_path URL for caching: {original_path[:80]}...")
                from app.services.storage import StorageService
                try:
                    cached_video_path = StorageService.download_video_from_url(
                        original_path, 
                        edit_job.video_id
                    )
                    cached_media_data["cached_video_path"] = cached_video_path
                    logger.info(f"Video cached locally: {cached_video_path}")
                except Exception as e:
                    logger.warning(f"Failed to download video from original_path URL: {e}")
        
        # Render video (use cached media_data to avoid DB connection timeout)
        editor = EditorService()
        result = editor.render_from_edl(
            video_id=edit_job.video_id,
            edl=ai_edl,
            edit_options=edit_options,
            media_data=cached_media_data  # Pass cached data to avoid DB query
        )
        
        # Update EditJob
        edit_job.output_paths = result["output_paths"]
        edit_job.status = EditJobStatus.COMPLETED
        edit_job.completed_at = datetime.utcnow()
        db.commit()
        
        # Update AI edit job if linked
        if ai_edit_job_id:
            try:
                ai_job = db.query(AIEditJob).filter(AIEditJob.id == ai_edit_job_id).first()
                if ai_job:
                    ai_job.output_paths = result["output_paths"]
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update AI edit job {ai_edit_job_id}: {e}")
        
        logger.info(f"AI edit rendering completed: EditJob {edit_job_id}")
        return {
            "edit_job_id": edit_job_id,
            "output_paths": result["output_paths"]
        }
        
    except Exception as e:
        logger.error(f"AI edit rendering failed for EditJob {edit_job_id}: {e}", exc_info=True)
        
        # Update job status
        if edit_job:
            try:
                edit_job.status = EditJobStatus.FAILED
                edit_job.error_message = str(e)[:500]
                edit_job.completed_at = datetime.utcnow()
                db.commit()
            except:
                pass
        
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def generate_ai_edit_task(self, job_id: str):
    """Generate AI-driven storytelling edit plan."""
    from app.services.ai.data_loader import DataLoader
    from app.services.ai.storytelling_agent import StorytellingAgent
    import asyncio
    
    db = SessionLocal()
    job = None
    try:
        job = db.query(AIEditJob).filter(AIEditJob.id == job_id).first()
        if not job:
            logger.error(f"AI edit job {job_id} not found.")
            return
        
        job.status = AIEditJobStatus.PROCESSING
        job.started_at = datetime.utcnow()  # DateTime field, not string
        db.commit()
        
        # Load data
        data_loader = DataLoader(db)
        data = data_loader.load_all_data(job.video_id)
        
        # Extract transcript segments
        transcript_segments = data_loader.extract_transcript_segments(
            data.get("transcription")
        )
        
        # Initialize agent
        agent = StorytellingAgent()
        
        # Generate edit plan (async call in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            plan = loop.run_until_complete(
                agent.generate_edit_plan(
                    frames=data.get("frames", []),
                    scenes=data.get("scenes", []),
                    transcript_segments=transcript_segments,
                    summary=job.summary or {},
                    story_prompt=job.story_prompt,
                    video_duration=data.get("video_duration", 0.0)
                )
            )
        finally:
            # Cleanup async resources
            try:
                # Close agent properly
                if hasattr(agent, 'llm_client') and agent.llm_client:
                    loop.run_until_complete(agent.llm_client.close())
            except Exception as e:
                logger.warning(f"Error closing LLM client: {e}")
            finally:
                loop.close()
        
        # Save plan
        job.llm_plan = plan
        job.compression_metadata = plan.get("metadata", {}).get("compression_ratios")
        job.validation_errors = plan.get("metadata", {}).get("validation_errors")
        job.llm_usage = plan.get("metadata", {}).get("llm_usage")
        job.status = AIEditJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()  # DateTime field, not string
        db.commit()
        
        logger.info(f"AI edit job {job_id} completed successfully.")
        return plan
        
    except Exception as e:
        logger.error(f"AI edit job {job_id} failed: {e}", exc_info=True)
        if job:
            job.status = AIEditJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()  # DateTime field, not string
            db.commit()
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()