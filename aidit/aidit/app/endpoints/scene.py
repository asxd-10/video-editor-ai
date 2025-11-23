"""
Scene indexing endpoint
"""
from fastapi import HTTPException
from typing import Dict, Any
import logging
import asyncio
import json

from ..database import Database, ProcessingStatus
from ..scene_indexer import SceneIndexer
from ..models import SceneIndexRequest

logger = logging.getLogger(__name__)


async def scene_index_endpoint(
    scene_indexer: SceneIndexer,
    video_file_cache: Dict[str, Any],
    request: SceneIndexRequest
) -> Dict[str, Any]:
    """
    Upload video to videodb, wait for upload, do scene indexing with non-blocking status check
    
    Uploads video, waits for upload completion, performs scene indexing,
    saves scene-level understanding for the video_id.
    
    Args:
        scene_indexer: SceneIndexer instance
        video_file_cache: Cache for video file objects
        request: SceneIndexRequest with video_id, video_url, extraction_type, prompt, etc.
        
    Returns:
        Dictionary with video_id, index_id, status, and scene data
    """
    if scene_indexer is None:
        raise HTTPException(status_code=503, detail="Scene indexing not available. Check VIDEODB_API_KEY.")
    
    try:
        video_id = request.video_id
        video_url = str(request.video_url)
        logger.info(f"Uploading video for scene indexing: {video_url} (ID: {video_id})")
        
        # Create media record
        Database.create_or_get_media(video_id, video_url, "video")
        
        # Upload video to videodb
        logger.info("Uploading video to videodb...")
        video_file = scene_indexer.upload_video(video_url)
        
        # Store video file object in cache
        video_file_cache[video_file.id] = video_file
        
        # Wait for upload with non-blocking status check
        logger.info("Waiting for video upload to complete...")
        max_wait_time = 300  # 5 minutes max
        wait_interval = 2  # Check every 2 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            # Check upload status (non-blocking)
            try:
                # videodb upload is typically synchronous, but we check status
                if hasattr(video_file, 'status'):
                    status = video_file.status
                    if status == 'ready' or status == 'completed':
                        break
                else:
                    # Assume ready if no status attribute
                    break
            except Exception as e:
                logger.warning(f"Error checking upload status: {str(e)}")
            
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval
        
        logger.info("Video upload completed, starting scene indexing...")
        
        # Build extraction config
        extraction_config = None
        if request.extraction_type == "shot_based":
            extraction_config = {
                "threshold": request.threshold or 20,
                "frame_count": request.frame_count or 5
            }
        
        # Start scene indexing
        index_id = scene_indexer.index_scenes(
            video_file_obj=video_file,
            extraction_type=request.extraction_type,
            extraction_config=extraction_config,
            prompt=request.prompt
        )
        
        # Save initial status
        Database.create_scene_index(
            video_id=video_id,
            video_db_id=video_file.id,
            index_id=index_id,
            extraction_type=request.extraction_type,
            prompt=request.prompt,
            status=ProcessingStatus.PROCESSING.value
        )
        
        # Poll for results (get_scene_index waits for completion)
        logger.info("Polling for scene index results...")
        scenes = scene_indexer.get_scene_index(video_file, index_id)
        
        # Save results to database
        Database.update_scene_index(
            video_id=video_id,
            index_id=index_id,
            status=ProcessingStatus.COMPLETED.value,
            scene_count=len(scenes),
            scenes_data=json.dumps(scenes)
        )
        
        logger.info(f"Scene indexing completed. Found {len(scenes)} scenes.")
        
        return {
            "success": True,
            "video_id": video_id,
            "index_id": index_id,
            "status": "completed",
            "scene_count": len(scenes),
            "scenes": scenes
        }
        
    except Exception as e:
        logger.error(f"Error in scene indexing: {str(e)}")
        if 'index_id' in locals():
            Database.update_scene_index(
                video_id=video_id,
                index_id=index_id,
                status=ProcessingStatus.FAILED.value,
                error_message=str(e)
            )
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

