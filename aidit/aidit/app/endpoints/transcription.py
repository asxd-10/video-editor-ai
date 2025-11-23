"""
Transcription endpoint
"""
from fastapi import HTTPException
from typing import Dict, Any
import logging
import asyncio
import json

from ..database import Database, ProcessingStatus
from ..scene_indexer import SceneIndexer
from ..models import TranscriptionRequest

logger = logging.getLogger(__name__)


async def transcription_endpoint(
    scene_indexer: SceneIndexer,
    video_file_cache: Dict[str, Any],
    request: TranscriptionRequest
) -> Dict[str, Any]:
    """
    Upload video to videodb, wait for upload, do transcription with non-blocking status check
    
    Uploads video, waits for upload completion, performs transcription,
    saves transcription data for the video_id.
    
    Args:
        scene_indexer: SceneIndexer instance
        video_file_cache: Cache for video file objects
        request: TranscriptionRequest with video_id, video_url
        
    Returns:
        Dictionary with video_id, status, and transcription data
    """
    logger.info(f"Received transcription request: video_id={request.video_id}, video_url={request.video_url}")
    
    if scene_indexer is None:
        raise HTTPException(status_code=503, detail="Transcription not available. Check VIDEODB_API_KEY.")
    
    try:
        video_id = request.video_id
        video_url = str(request.video_url)
        logger.info(f"Uploading video for transcription: {video_url} (ID: {video_id})")
        
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
        
        logger.info("Video upload completed, starting transcription...")
        
        # Check if transcription record exists, create or update
        existing_transcription = Database.get_transcription(video_id)
        if existing_transcription:
            # Update existing record
            Database.update_transcription(
                video_id=video_id,
                video_db_id=video_file.id,
                status=ProcessingStatus.PROCESSING.value
            )
        else:
            # Create new record
            Database.create_transcription(
                video_id=video_id,
                video_db_id=video_file.id,
                status=ProcessingStatus.PROCESSING.value
            )
        
        # Start transcription indexing
        try:
            scene_indexer.index_spoken_words(
                video_file_obj=video_file
            )
            
            # Poll for transcript (get_transcript waits for completion)
            logger.info("Polling for transcription results...")
            transcript = scene_indexer.get_transcript(video_file)
        except Exception as e:
            error_msg = str(e)
            # Check if it's a "no spoken data" error
            if "no spoken data" in error_msg.lower() or "failed to detect the language" in error_msg.lower():
                logger.info("No spoken data found in video. Saving empty transcription.")
                transcript = None
            else:
                # Re-raise other errors
                raise
        
        # Extract full transcript text
        transcript_text = None
        segment_count = 0
        
        if transcript and isinstance(transcript, list) and len(transcript) > 0:
            transcript_text = " ".join([seg.get("text", "") for seg in transcript if isinstance(seg, dict)])
            segment_count = len(transcript)
        
        # Save results to database (even if empty/None)
        Database.update_transcription(
            video_id=video_id,
            status=ProcessingStatus.COMPLETED.value,
            segment_count=segment_count,
            transcript_data=json.dumps(transcript) if transcript else None,
            transcript_text=transcript_text
        )
        
        logger.info(f"Transcription completed. Found {segment_count} segments.")
        
        return {
            "success": True,
            "video_id": video_id,
            "status": "completed",
            "segment_count": segment_count,
            "transcript_text": transcript_text,
            "transcript_data": transcript
        }
        
    except Exception as e:
        logger.error(f"Error in transcription: {str(e)}")
        Database.update_transcription(
            video_id=video_id,
            status=ProcessingStatus.FAILED.value,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

