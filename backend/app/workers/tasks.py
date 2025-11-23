from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.media import Media, MediaStatus, MediaType
from app.models.video import VideoAsset, ProcessingLog, VideoQuality  # Keep VideoAsset for now
from app.models.edit_job import EditJob, EditJobStatus
from app.models.ai_edit_job import AIEditJob, AIEditJobStatus
from app.services.video_processor import VideoProcessor
from app.services.storage import StorageService
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import json

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
        cached_media_data = edit_options.pop("_media_data", None)  # Cached for single video
        multi_video_data = edit_options.pop("_multi_video_data", None)  # Cached for multi-video
        
        if not ai_edl:
            raise ValueError("No EDL found in edit_options")
        
        # Determine if this is a multi-video edit
        is_multi_video = multi_video_data is not None and len(multi_video_data) > 1
        
        # Download and cache video file(s) if they're URLs (S3 or HTTP)
        # This avoids network issues during rendering and database connection timeouts
        if is_multi_video:
            # Download and cache all videos for multi-video edit
            for vid_id, vid_data in multi_video_data.items():
                video_url = vid_data.get("video_url")
                original_path = vid_data.get("original_path")
                
                cached_video_path = None
                if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
                    logger.info(f"Downloading video {vid_id} from URL for caching: {video_url[:80]}...")
                    try:
                        cached_video_path = StorageService.download_video_from_url(
                            video_url, 
                            vid_id
                        )
                        vid_data["cached_video_path"] = cached_video_path
                        logger.info(f"Video {vid_id} cached locally: {cached_video_path}")
                    except Exception as e:
                        logger.warning(f"Failed to download video {vid_id} from URL: {e}")
                elif original_path and (original_path.startswith('http://') or original_path.startswith('https://')):
                    logger.info(f"Downloading video {vid_id} from original_path URL: {original_path[:80]}...")
                    try:
                        cached_video_path = StorageService.download_video_from_url(
                            original_path, 
                            vid_id
                        )
                        vid_data["cached_video_path"] = cached_video_path
                        logger.info(f"Video {vid_id} cached locally: {cached_video_path}")
                    except Exception as e:
                        logger.warning(f"Failed to download video {vid_id} from original_path URL: {e}")
        elif cached_media_data:
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
            media_data=cached_media_data,  # Pass cached data for single video
            multi_video_data=multi_video_data  # Pass cached data for multi-video
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
def generate_ai_edit_task_standalone(
    self,
    job_id: str,
    videos_data: List[Dict[str, Any]],
    summary: Dict[str, Any],
    story_prompt: Dict[str, Any],
    data: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    videos_metadata: Optional[List[Dict]] = None
):
    """
    Generate AI-driven storytelling edit plan (standalone, no database).
    
    All data is provided in the function arguments - no database queries.
    """
    from app.services.ai.storytelling_agent import StorytellingAgent
    import asyncio
    
    try:
        logger.info(f"Starting AI edit job {job_id} (standalone mode, no database)")
        
        # Determine if this is a multi-video edit
        is_multi_video = len(videos_data) > 1
        video_ids = [v["video_id"] for v in videos_data]
        
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
                    summary=summary or {},
                    story_prompt=story_prompt,
                    video_duration=data.get("video_duration", 0.0),
                    video_ids=video_ids if is_multi_video else None,
                    videos_metadata=videos_metadata
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
        
        logger.info(f"AI edit job {job_id} completed successfully (standalone mode).")
        return plan
        
    except Exception as e:
        logger.error(f"AI edit job {job_id} failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def generate_and_apply_ai_edit_pipeline(
    self,
    job_id: str,
    videos_data: List[Dict[str, Any]],
    summary: Dict[str, Any],
    story_prompt: Dict[str, Any],
    data: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    videos_metadata: Optional[List[Dict]] = None,
    aspect_ratios: List[str] = ["16:9"],
    primary_video_id: str = None,
    callback_url: Optional[str] = None,
    callback_data: Optional[Dict] = None
):
    """
    Complete pipeline: Generate AI edit plan -> Apply edit -> Save to processed_dir -> Upload to S3.
    
    Self-sufficient: All data provided in arguments, no database queries.
    
    Args:
        job_id: Unique job identifier
        videos_data: List of video data dictionaries
        summary: Summary data
        story_prompt: Story prompt data
        data: Pre-processed data (frames, scenes, etc.)
        transcript_segments: Transcript segments
        videos_metadata: Optional video metadata for multi-video edits
        aspect_ratios: List of aspect ratios to render
        primary_video_id: Primary video ID for output directory
        callback_url: Optional callback URL
        callback_data: Optional callback data
    """
    from app.services.ai.storytelling_agent import StorytellingAgent
    from app.services.ai.edl_converter import EDLConverter
    from app.services.editor import EditorService
    from app.services.storage import StorageService
    import asyncio
    from pathlib import Path
    import shutil
    
    try:
        logger.info(f"Starting AI edit pipeline {job_id} (generate + apply + save)")
        
        # Step 1: Generate AI edit plan
        logger.info(f"Pipeline {job_id}: Step 1 - Generating AI edit plan")
        is_multi_video = len(videos_data) > 1
        video_ids = [v["video_id"] for v in videos_data]
        
        # Initialize agent
        agent = StorytellingAgent()
        
        # Generate edit plan (async call in sync context)
        # CRITICAL: loop.run_until_complete() ensures Step 1 (generate) completes BEFORE Step 2 (apply)
        # This is sequential execution - no parallel processing possible
        logger.info(f"Pipeline {job_id}: Starting Step 1 - Generate (will wait for completion before Step 2)")
        logger.info(f"Pipeline {job_id}: Data received - {len(data.get('frames', []))} frames, {len(data.get('scenes', []))} scenes")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            plan = loop.run_until_complete(
                agent.generate_edit_plan(
                    frames=data.get("frames", []),
                    scenes=data.get("scenes", []),
                    transcript_segments=transcript_segments,
                    summary=summary or {},
                    story_prompt=story_prompt,
                    video_duration=data.get("video_duration", 0.0),
                    video_ids=video_ids if is_multi_video else None,
                    videos_metadata=videos_metadata
                )
            )
        finally:
            try:
                if hasattr(agent, 'llm_client') and agent.llm_client:
                    loop.run_until_complete(agent.llm_client.close())
            except Exception as e:
                logger.warning(f"Error closing LLM client: {e}")
            finally:
                loop.close()
        
        logger.info(f"Pipeline {job_id}: Step 1 completed - Edit plan generated")
        
        # CRITICAL: Step 1 is now complete. Only proceed to Step 2 after plan is fully generated.
        # This ensures synchronous execution - apply cannot start before generate completes.
        
        # Step 2: Convert EDL and prepare for rendering
        logger.info(f"Pipeline {job_id}: Step 2 - Converting EDL and preparing for rendering (Step 1 completed, proceeding sequentially)")
        converter = EDLConverter()
        editor_edl = converter.convert_llm_edl_to_editor_format(
            plan.get("edl", [])
        )
        
        if not editor_edl or len(editor_edl) == 0:
            raise ValueError("No valid segments in edit plan. EDL is empty after conversion.")
        
        # Create edit options
        edit_options = converter.create_edit_options_from_plan(plan)
        edit_options["aspect_ratios"] = aspect_ratios
        
        # Step 3: Download and cache video files
        logger.info(f"Pipeline {job_id}: Step 3 - Downloading and caching video files")
        multi_video_data = {}
        cached_media_data = None
        
        if is_multi_video:
            # Multi-video: download all videos
            for vid_data in videos_data:
                vid_id = vid_data["video_id"]
                video_url = vid_data.get("video_url")
                
                if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
                    logger.info(f"Downloading video {vid_id} from URL: {video_url[:80]}...")
                    try:
                        cached_path = StorageService.download_video_from_url(video_url, vid_id)
                        multi_video_data[vid_id] = {
                            "video_url": video_url,
                            "cached_video_path": cached_path,
                            "duration_seconds": vid_data.get("duration_seconds", 0.0),
                            "has_audio": True
                        }
                        logger.info(f"Video {vid_id} cached: {cached_path}")
                    except Exception as e:
                        logger.warning(f"Failed to download video {vid_id}, using URL directly: {e}")
                        multi_video_data[vid_id] = {
                            "video_url": video_url,
                            "duration_seconds": vid_data.get("duration_seconds", 0.0),
                            "has_audio": True
                        }
                else:
                    multi_video_data[vid_id] = {
                        "video_url": video_url,
                        "duration_seconds": vid_data.get("duration_seconds", 0.0),
                        "has_audio": True
                    }
        else:
            # Single video
            vid_data = videos_data[0]
            video_url = vid_data.get("video_url")
            vid_id = vid_data["video_id"]
            
            if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
                logger.info(f"Downloading video from URL: {video_url[:80]}...")
                try:
                    cached_path = StorageService.download_video_from_url(video_url, vid_id)
                    cached_media_data = {
                        "video_url": video_url,
                        "cached_video_path": cached_path,
                        "duration_seconds": vid_data.get("duration_seconds", 0.0),
                        "has_audio": True
                    }
                    logger.info(f"Video cached: {cached_path}")
                except Exception as e:
                    logger.warning(f"Failed to download video, using URL directly: {e}")
                    cached_media_data = {
                        "video_url": video_url,
                        "duration_seconds": vid_data.get("duration_seconds", 0.0),
                        "has_audio": True
                    }
            else:
                cached_media_data = {
                    "video_url": video_url,
                    "duration_seconds": vid_data.get("duration_seconds", 0.0),
                    "has_audio": True
                }
        
        # Step 4: Render videos
        logger.info(f"Pipeline {job_id}: Step 4 - Rendering videos for aspect ratios: {aspect_ratios}")
        editor = EditorService()
        # Use job_id as output_video_id to ensure unique filenames per job (avoid file collisions)
        output_video_id = job_id  # Use job_id instead of primary_video_id to avoid reusing old files
        
        result = editor.render_from_edl(
            video_id=output_video_id,
            edl=editor_edl,
            edit_options=edit_options,
            media_data=cached_media_data,  # For single video
            multi_video_data=multi_video_data if is_multi_video else None  # For multi-video
        )
        
        output_paths = result.get("output_paths", {})
        logger.info(f"Pipeline {job_id}: Step 4 completed - Videos rendered: {list(output_paths.keys())}")
        
        # Step 5: Ensure files are saved to processed_dir and optionally upload to S3
        logger.info(f"Pipeline {job_id}: Step 5 - Saving to processed_dir and uploading to S3")
        local_paths = {}
        uploaded_urls = {}
        
        for aspect_ratio, output_path in output_paths.items():
            if isinstance(output_path, str):
                # Handle web-style paths like "/storage/processed/..." 
                # Convert to actual file system path
                if output_path.startswith("/storage/"):
                    # Convert /storage/processed/video_id/file.mp4 to actual file system path
                    from app.config import get_settings
                    settings = get_settings()
                    relative_path = output_path.replace("/storage/", "")
                    output_path_resolved = settings.BASE_STORAGE_PATH / relative_path
                else:
                    # Resolve relative paths to absolute paths
                    output_path_resolved = Path(output_path).resolve()
                
                if output_path_resolved.exists():
                    # Ensure file is in processed_dir
                    processed_dir = StorageService.get_processed_directory(output_video_id)
                    expected_path = processed_dir / f"edited_{aspect_ratio.replace(':', '_')}.mp4"
                    
                    # If file is not in processed_dir, copy it there
                    if output_path_resolved != expected_path.resolve():
                        if not expected_path.exists():
                            shutil.copy2(str(output_path_resolved), expected_path)
                            logger.info(f"Copied video to processed_dir: {expected_path}")
                        local_path = str(expected_path)
                    else:
                        local_path = str(output_path_resolved)
                    
                    local_paths[aspect_ratio] = local_path
                    logger.info(f"Video {aspect_ratio} saved to processed_dir: {local_path}")
                    
                    # Optionally upload to S3 (if callback_url is provided, we probably want S3)
                    if callback_url:
                        try:
                            public_url = StorageService.upload_to_supabase_storage(
                                file_path=local_path,
                                bucket_name="videos",
                                folder_path=f"ai-edits/{job_id}",
                                filename=f"edited_{aspect_ratio.replace(':', '_')}.mp4"
                            )
                            if public_url:  # Only set if upload succeeded
                                uploaded_urls[aspect_ratio] = public_url
                                logger.info(f"Uploaded {aspect_ratio} video to S3: {public_url}")
                            else:
                                logger.warning(f"Skipped S3 upload for {aspect_ratio} (credentials not configured)")
                        except Exception as e:
                            logger.error(f"Failed to upload {aspect_ratio} video to S3: {e}", exc_info=True)
                            # Continue even if upload fails
                else:
                    logger.warning(f"Output path does not exist: {output_path} (resolved: {output_path_resolved})")
            else:
                logger.warning(f"Output path is not a string for {aspect_ratio}: {type(output_path)}")
        
        # Step 6: Callback (if provided)
        if callback_url:
            logger.info(f"Pipeline {job_id}: Step 6 - Calling back: {callback_url}")
            try:
                # Get storage_url (prefer uploaded S3 URL, fallback to first local path if no upload)
                storage_url = None
                if uploaded_urls:
                    # Use first uploaded URL (S3/Supabase)
                    storage_url = list(uploaded_urls.values())[0]
                elif local_paths:
                    # Fallback: use first local path (though webhook probably needs a URL)
                    storage_url = list(local_paths.values())[0]
                    logger.warning(f"No S3 upload available, using local path for storage_url: {storage_url}")
                
                # Build callback payload: {storage_url, callback_data: {...}}
                # Webhook expects callback_data to be nested, not spread at top level
                callback_payload = {
                    "storage_url": storage_url,
                    "callback_data": callback_data or {}  # Nest callback_data as expected by webhook
                }
                
                # Log the exact payload being sent (for debugging webhook API compatibility)
                logger.info(f"Callback payload being sent to {callback_url}:")
                logger.info(f"  storage_url: {storage_url}")
                logger.info(f"  callback_data: {callback_data}")
                logger.info(f"  Full payload: {json.dumps(callback_payload, indent=2)}")
                
                import httpx
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        callback_url,
                        json=callback_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code >= 400:
                        # Log error response for debugging
                        error_text = response.text[:1000] if response.text else "No error message"
                        logger.error(f"Callback failed ({response.status_code}): {error_text}")
                        logger.error(f"Request payload was: {json.dumps(callback_payload, indent=2)}")
                    response.raise_for_status()
                    logger.info(f"Callback successful. Response: {response.status_code}")
            except Exception as e:
                logger.error(f"Callback failed: {e}", exc_info=True)
                # Don't fail the whole pipeline if callback fails
        
        logger.info(f"Pipeline {job_id} completed successfully")
        return {
            "job_id": job_id,
            "status": "completed",
            "local_paths": local_paths,
            "uploaded_urls": uploaded_urls if uploaded_urls else None,
            "plan": plan
        }
        
    except Exception as e:
        logger.error(f"Pipeline {job_id} failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


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