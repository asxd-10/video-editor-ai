"""
Batch processing endpoint - processes multiple media items concurrently
"""
from fastapi import HTTPException, UploadFile
from typing import Dict, Any, List, Optional
import logging
import asyncio
from urllib.parse import urlparse
import mimetypes
from ..models import VideoProcessRequest, SceneIndexRequest, TranscriptionRequest
from ..database import get_supabase_client
from ..video_index import VideoIndex
from ..video_processor import VideoProcessor
from ..scene_indexer import SceneIndexer
from .image import process_image_endpoint
from .video import process_video_endpoint
from .scene import scene_index_endpoint
from .transcription import transcription_endpoint

logger = logging.getLogger(__name__)


def is_image_url(url: str) -> bool:
    """Determine if URL points to an image based on extension or content type"""
    url_lower = url.lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    
    # Check file extension
    parsed = urlparse(url_lower)
    path = parsed.path
    if any(path.endswith(ext) for ext in image_extensions):
        return True
    
    # Check MIME type if available
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type and mime_type.startswith('image/'):
        return True
    
    return False


async def process_image_item(
    video_index: VideoIndex,
    file_id: str,
    image_url: str,
    prompt: str = "What's in this image?",
    model: str = "google/gemini-2.0-flash-001"
) -> Dict[str, Any]:
    """Process a single image item"""
    try:
        result = await process_image_endpoint(
            video_index=video_index,
            file_id=file_id,
            image=None,
            image_url=image_url,
            prompt=prompt,
            model=model
        )
        return {
            "file_id": file_id,
            "type": "image",
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error processing image {file_id}: {str(e)}")
        return {
            "file_id": file_id,
            "type": "image",
            "status": "error",
            "error": str(e)
        }


async def process_video_item(
    video_processor: VideoProcessor,
    video_index: VideoIndex,
    scene_indexer: Optional[SceneIndexer],
    video_file_cache: Dict[str, Any],
    video_id: str,
    video_url: str,
    granularity_seconds: float = 1.0,
    prompt: str = "What's in this image?",
    model: str = "google/gemini-2.0-flash-001",
    extraction_type: str = "shot_based",
    scene_prompt: str = "describe the image in 100 words",
    threshold: int = 20,
    frame_count: int = 5
) -> Dict[str, Any]:
    """Process a single video item through all 3 video endpoints concurrently"""
    results = {
        "video_id": video_id,
        "type": "video",
        "status": "processing",
        "results": {}
    }
    
    async def process_video_frames():
        """Process video frames"""
        try:
            request = VideoProcessRequest(
                video_id=video_id,
                video_url=video_url,
                granularity_seconds=granularity_seconds,
                prompt=prompt,
                model=model
            )
            result = await process_video_endpoint(
                video_processor=video_processor,
                video_index=video_index,
                request=request
            )
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error processing video frames for {video_id}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def process_scene_index():
        """Process scene indexing"""
        if scene_indexer is None:
            return {"status": "skipped", "error": "Scene indexing not available"}
        try:
            request = SceneIndexRequest(
                video_id=video_id,
                video_url=video_url,
                extraction_type=extraction_type,
                prompt=scene_prompt,
                threshold=threshold,
                frame_count=frame_count
            )
            result = await scene_index_endpoint(
                scene_indexer=scene_indexer,
                video_file_cache=video_file_cache,
                request=request
            )
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error processing scene index for {video_id}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def process_transcription():
        """Process transcription"""
        if scene_indexer is None:
            return {"status": "skipped", "error": "Transcription not available"}
        try:
            request = TranscriptionRequest(
                video_id=video_id,
                video_url=video_url
            )
            result = await transcription_endpoint(
                scene_indexer=scene_indexer,
                video_file_cache=video_file_cache,
                request=request
            )
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error processing transcription for {video_id}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    # Run all 3 video processing tasks concurrently
    try:
        frame_result, scene_result, transcript_result = await asyncio.gather(
            process_video_frames(),
            process_scene_index(),
            process_transcription(),
            return_exceptions=True
        )
        
        results["results"]["video_frames"] = frame_result if not isinstance(frame_result, Exception) else {"status": "error", "error": str(frame_result)}
        results["results"]["scene_index"] = scene_result if not isinstance(scene_result, Exception) else {"status": "error", "error": str(scene_result)}
        results["results"]["transcription"] = transcript_result if not isinstance(transcript_result, Exception) else {"status": "error", "error": str(transcript_result)}
        
        # Determine overall status
        all_success = all(
            r.get("status") == "success" 
            for r in results["results"].values()
        )
        results["status"] = "completed" if all_success else "partial"
        
    except Exception as e:
        logger.error(f"Error in batch video processing for {video_id}: {str(e)}")
        results["status"] = "error"
        results["error"] = str(e)
    
    return results


async def batch_process_endpoint(
    video_index: VideoIndex,
    video_processor: VideoProcessor,
    scene_indexer: Optional[SceneIndexer],
    video_file_cache: Dict[str, Any],
    media_items: List[Dict[str, str]],
    frame_prompt: str = "What's in this image?",
    model: str = "google/gemini-2.0-flash-001",
    granularity_seconds: float = 1.0,
    scene_prompt: str = "describe the image in 100 words",
    extraction_type: str = "shot_based",
    threshold: int = 20,
    frame_count: int = 5
) -> Dict[str, Any]:
    """
    Process a batch of media items concurrently
    
    Args:
        video_index: VideoIndex instance
        video_processor: VideoProcessor instance
        scene_indexer: SceneIndexer instance (optional)
        video_file_cache: Cache for video file objects
        media_items: List of dicts with "video_id" and "video_url" keys
        prompt: Prompt for image/video frame processing
        model: Model to use for LLM processing
        granularity_seconds: Granularity for video frame extraction
        scene_prompt: Prompt for scene indexing
        extraction_type: Scene extraction type
        threshold: Scene detection threshold
        frame_count: Number of frames per scene
        
    Returns:
        Dictionary with results for all processed items
    """
    tasks = []
    supabase_client = get_supabase_client()

    # ensure unique media_items
    media_items = list(set(media_items))
    
    for item in media_items:
        # Get media_id from item (could be video_id, file_id, or media_id)
        media_id = item
        
        if not media_id:
            logger.warning(f"Skipping item with missing media_id: {item}")
            continue
        
        # Get storage_path from attachments table
        try:
            
            attachments_result = supabase_client.table("attachments").select("storage_path").eq("message_id", media_id).execute()
            
            if not attachments_result.data or len(attachments_result.data) == 0:
                logger.warning(f"No attachment found for media_id: {media_id}")
                continue
            
            media_path = attachments_result.data[0].get("storage_path")
            if not media_path:
                logger.warning(f"No storage_path found for media_id: {media_id}")
                continue
            
            # Get public URL from Supabase storage
            media_s3_path = supabase_client.storage.from_("videos").get_public_url(media_path)
        except Exception as e:
            logger.error(f"Error fetching media path for {media_id}: {str(e)}")
            continue
        
        # Use media_id as the identifier
        video_id = media_id
        
        # Determine if it's an image or video
        if is_image_url(media_s3_path):
            # Process as image
            task = process_image_item(
                video_index=video_index,
                file_id=video_id,
                image_url=media_s3_path,
                prompt=frame_prompt,
                model=model
            )
        else:
            # Process as video (all 3 endpoints)
            task = process_video_item(
                video_processor=video_processor,
                video_index=video_index,
                scene_indexer=scene_indexer,
                video_file_cache=video_file_cache,
                video_id=video_id,
                video_url=media_s3_path,
                granularity_seconds=granularity_seconds,
                prompt=frame_prompt,
                model=model,
                extraction_type=extraction_type,
                scene_prompt=scene_prompt,
                threshold=threshold,
                frame_count=frame_count
            )
        
        tasks.append(task)
    
    # Process all items concurrently
    logger.info(f"Processing {len(tasks)} media items concurrently...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Format results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "index": i,
                "status": "error",
                "error": str(result)
            })
        else:
            processed_results.append(result)
    
    # Count successes
    success_count = sum(1 for r in processed_results if r.get("status") in ["success", "completed"])
    error_count = sum(1 for r in processed_results if r.get("status") == "error")
    partial_count = sum(1 for r in processed_results if r.get("status") == "partial")
    
    return {
        "success": True,
        "total_items": len(media_items),
        "processed": len(processed_results),
        "successful": success_count,
        "partial": partial_count,
        "failed": error_count,
        "results": processed_results
    }

