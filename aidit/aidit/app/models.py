"""
Pydantic models for API requests
"""
from typing_extensions import Union
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict


class ImageProcessRequest(BaseModel):
    file_id: str  # Required index for the image
    image_url: Optional[str] = None  # URL of image (sent directly to LLM)
    prompt: Optional[str] = "What's in this image?"
    model: Optional[str] = "google/gemini-2.0-flash-001"


class VideoProcessRequest(BaseModel):
    video_id: str  # Required index for the video
    video_url: HttpUrl
    granularity_seconds: Optional[float] = 1.0
    prompt: Optional[str] = "What's in this image?"
    model: Optional[str] = "google/gemini-2.0-flash-001"


class SceneIndexRequest(BaseModel):
    video_id: str  # Required index for the video
    video_url: HttpUrl
    extraction_type: Optional[str] = "shot_based"
    prompt: Optional[str] = "describe the image in 100 words"
    threshold: Optional[int] = 20
    frame_count: Optional[int] = 5


class TranscriptionRequest(BaseModel):
    video_id: str  # Required index for the video
    video_url: HttpUrl


class BatchProcessRequest(BaseModel):
    """Request model for batch processing"""
    media_items: List[Union[str, int]]  # List of media IDs or message IDs
    prompt: Optional[str] = "What's in this image?"
    model: Optional[str] = "google/gemini-2.0-flash-001"
    granularity_seconds: Optional[float] = 1.0
    scene_prompt: Optional[str] = "describe the image in 100 words"
    extraction_type: Optional[str] = "shot_based"
    threshold: Optional[int] = 20
    frame_count: Optional[int] = 5

