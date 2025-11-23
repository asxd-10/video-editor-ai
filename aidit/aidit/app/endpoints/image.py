"""
Image processing endpoint
"""
from fastapi import HTTPException, UploadFile, File
from typing import Optional, Dict, Any
import logging
import os

from ..database import Database, ProcessingStatus
from ..video_index import VideoIndex
from ..utils import encode_image_to_base64

logger = logging.getLogger(__name__)


async def process_image_endpoint(
    video_index: VideoIndex,
    file_id: str,
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = None,
    prompt: Optional[str] = "What's in this image?",
    model: Optional[str] = "google/gemini-2.0-flash-001"
) -> Dict[str, Any]:
    """
    Process a single image from URL or file upload
    
    Takes in URL or file, saves the extracted data to the database.
    
    Args:
        video_index: VideoIndex instance for LLM processing
        file_id: Required index for the image
        image: Image file upload (optional)
        image_url: URL of image to process (optional) - sent directly to LLM
        prompt: Prompt/question to ask about the image
        model: Model to use
        
    Returns:
        Dictionary with response and processing information
    """
    try:
        # Handle file upload (convert to base64)
        if image:
            logger.info(f"Processing uploaded image file: {image.filename}")
            image_bytes = await image.read()
            base64_image = encode_image_to_base64(image_bytes)
            
            result = video_index.process_image_from_base64(
                base64_image,
                prompt or "What's in this image?"
            )
            source = f"file:{image.filename}"
            media_url = f"uploaded:{image.filename}"
        
        # Handle URL or local file path
        elif image_url:
            # Check if it's a local file path or a URL
            is_url = image_url.startswith(('http://', 'https://', 's3://'))
            
            if is_url:
                # It's a real URL, send directly to LLM
                logger.info(f"Processing image from URL: {image_url}")
                result = video_index.process_image_from_url(
                    image_url,
                    prompt or "What's in this image?"
                )
                source = f"url:{image_url}"
                media_url = image_url
            else:
                # It's a local file path, read and convert to base64
                logger.info(f"Processing image from file path: {image_url}")
                if not os.path.exists(image_url):
                    raise HTTPException(status_code=404, detail=f"Image file not found: {image_url}")
                
                # Read file and convert to base64
                with open(image_url, "rb") as f:
                    image_bytes = f.read()
                
                base64_image = encode_image_to_base64(image_bytes)
                
                result = video_index.process_image_from_base64(
                    base64_image,
                    prompt or "What's in this image?"
                )
                source = f"path:{image_url}"
                media_url = image_url
        
        else:
            raise HTTPException(status_code=400, detail="Either image file or image_url must be provided")
        
        # Save to database
        Database.create_or_get_media(file_id, media_url, "image")
        
        # Check if image processing exists, update most recent or create new
        existing = Database.get_image_processing(file_id)
        if existing:
            Database.update_image_processing(
                video_id=file_id,
                prompt=prompt or "What's in this image?",
                model=model,
                llm_response=result.get("response", ""),
                status=ProcessingStatus.COMPLETED.value
            )
        else:
            Database.create_image_processing(
                video_id=file_id,
                prompt=prompt or "What's in this image?",
                model=model,
                llm_response=result.get("response", ""),
                status=ProcessingStatus.COMPLETED.value
            )
        
        return {
            "success": True,
            "file_id": file_id,
            "result": result,
            "source": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

