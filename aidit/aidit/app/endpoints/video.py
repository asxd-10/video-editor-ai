"""
Video processing endpoint
"""
from fastapi import HTTPException
from typing import Dict, Any
import logging
import os
import asyncio

from ..database import Database, ProcessingStatus
from ..video_index import VideoIndex
from ..video_processor import VideoProcessor
from ..models import VideoProcessRequest

logger = logging.getLogger(__name__)


async def process_video_endpoint(
    video_processor: VideoProcessor,
    video_index: VideoIndex,
    request: VideoProcessRequest
) -> Dict[str, Any]:
    """
    Process video frames concurrently
    
    Downloads video, splits by granularity (seconds), processes each frame
    concurrently using async calls, saves frame-level data to database.
    
    Args:
        video_processor: VideoProcessor instance
        video_index: VideoIndex instance for LLM processing
        request: VideoProcessRequest with video_id, video_url, granularity_seconds, prompt, model
        
    Returns:
        Dictionary with video_id, status, and frame processing summary
    """
    try:
        video_id = request.video_id
        video_url = str(request.video_url)
        granularity = request.granularity_seconds or 1.0
        
        logger.info(f"Processing video: {video_url} (ID: {video_id}, Granularity: {granularity}s)")
        
        # Create media record
        Database.create_or_get_media(video_id, video_url, "video")
        
        # Create video processing record
        video_processing = Database.create_or_get_video_processing(
            video_id=video_id,
            status=ProcessingStatus.PROCESSING.value,
            granularity_seconds=granularity,
            prompt=request.prompt,
            model=request.model
        )
        
        # Download video
        logger.info("Downloading video...")
        video_path = video_processor.download_video(video_url)
        
        try:
            # Split video into frames
            logger.info(f"Splitting video into frames (granularity: {granularity}s)...")
            frames = video_processor.split_video_by_granularity(video_path, granularity)
            
            total_frames = len(frames)
            Database.update_video_processing(video_id, total_frames=total_frames)
            
            # Logging (non-blocking - won't fail if table is missing columns)
            try:
                Database.create_log(video_id, None, "INFO", f"Extracted {total_frames} frames")
            except Exception as log_error:
                logger.warning(f"Could not create log entry: {str(log_error)}")
            
            logger.info(f"Processing {total_frames} frames concurrently...")
            
            # Process frames concurrently using asyncio
            async def process_frame(frame_data: tuple) -> Dict[str, Any]:
                """Process a single frame asynchronously"""
                frame_num, timestamp, frame_bytes = frame_data
                try:
                    # Convert frame to base64
                    base64_image = video_processor.frame_bytes_to_base64(frame_bytes)
                    
                    # Process with LLM
                    result = await asyncio.to_thread(
                        video_index.process_image_from_base64,
                        base64_image,
                        request.prompt or "What's in this image?"
                    )
                    
                    # Save frame to database
                    frame_record = Database.create_frame(
                        video_id=video_id,
                        frame_number=frame_num,
                        timestamp_seconds=timestamp,
                        status=ProcessingStatus.COMPLETED.value,
                        llm_response=result.get("response", "")
                    )
                    
                    return {
                        "frame_number": frame_num,
                        "timestamp": timestamp,
                        "status": "completed",
                        "frame_id": frame_record.get("id")
                    }
                except Exception as e:
                    logger.error(f"Error processing frame {frame_num}: {str(e)}")
                    # Save failed frame
                    Database.create_frame(
                        video_id=video_id,
                        frame_number=frame_num,
                        timestamp_seconds=timestamp,
                        status=ProcessingStatus.FAILED.value,
                        error_message=str(e)
                    )
                    return {
                        "frame_number": frame_num,
                        "timestamp": timestamp,
                        "status": "failed",
                        "error": str(e)
                    }
            
            # Process all frames concurrently
            tasks = [process_frame(frame_data) for frame_data in frames]
            results = await asyncio.gather(*tasks)
            
            # Count successes and failures
            processed = sum(1 for r in results if r.get("status") == "completed")
            failed = sum(1 for r in results if r.get("status") == "failed")
            
            # Update video processing status
            Database.update_video_processing(
                video_id=video_id,
                status=ProcessingStatus.COMPLETED.value,
                processed_frames=processed,
                failed_frames=failed
            )
            
            # Logging (non-blocking - won't fail if table is missing columns)
            try:
                Database.create_log(video_id, None, "INFO", f"Processed {processed} frames, {failed} failed")
            except Exception as log_error:
                logger.warning(f"Could not create log entry: {str(log_error)}")
            
            return {
                "success": True,
                "video_id": video_id,
                "status": "completed",
                "total_frames": total_frames,
                "processed_frames": processed,
                "failed_frames": failed,
                "message": f"Video processing completed. {processed}/{total_frames} frames processed successfully."
            }
            
        finally:
            # Clean up downloaded video file
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"Cleaned up video file: {video_path}")
                except Exception as e:
                    logger.warning(f"Could not remove video file: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        Database.update_video_processing(
            video_id=request.video_id,
            status=ProcessingStatus.FAILED.value,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

