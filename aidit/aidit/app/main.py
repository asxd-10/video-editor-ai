"""
FastAPI application for video and image processing with LLM integration
Simplified to 4 core endpoints with clean modular structure
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import logging

from .models import VideoProcessRequest, SceneIndexRequest, TranscriptionRequest, BatchProcessRequest
from .database import Database
from .video_index import VideoIndex
from .video_processor import VideoProcessor
from .scene_indexer import SceneIndexer

# Import endpoint handlers
from .endpoints.image import process_image_endpoint
from .endpoints.video import process_video_endpoint
from .endpoints.scene import scene_index_endpoint
from .endpoints.transcription import transcription_endpoint
from .endpoints.batch import batch_process_endpoint
from .models import BatchProcessRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Video Index API", version="2.0.0")

# Add exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Log validation errors for debugging"""
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(await request.body())}
    )

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
video_index = VideoIndex()
video_processor = VideoProcessor(video_index=video_index)

# Initialize scene indexer
try:
    scene_indexer = SceneIndexer()
    video_file_cache: Dict[str, Any] = {}
except Exception as e:
    logger.warning(f"SceneIndexer not available: {str(e)}")
    scene_indexer = None
    video_file_cache = {}


# Endpoint 1: Process image/frame with file_id
@app.post("/process/image")
async def process_image(
    file_id: str,
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = None,
    prompt: Optional[str] = "What's in this image?",
    model: Optional[str] = "google/gemini-2.0-flash-001"
):
    """Process a single image from URL or file upload"""
    return await process_image_endpoint(
        video_index=video_index,
        file_id=file_id,
        image=image,
        image_url=image_url,
        prompt=prompt,
        model=model
    )


# Endpoint 2: Process video frames (async concurrent)
@app.post("/process/video")
async def process_video_frames(request: VideoProcessRequest):
    """Process video frames concurrently"""
    return await process_video_endpoint(
        video_processor=video_processor,
        video_index=video_index,
        request=request
    )


# Endpoint 3: Scene indexing
@app.post("/scene/index")
async def scene_index(request: SceneIndexRequest):
    """Upload video to videodb and perform scene indexing"""
    return await scene_index_endpoint(
        scene_indexer=scene_indexer,
        video_file_cache=video_file_cache,
        request=request
    )


# Endpoint 4: Transcription
@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest):
    """Upload video to videodb and perform transcription"""
    return await transcription_endpoint(
        scene_indexer=scene_indexer,
        video_file_cache=video_file_cache,
        request=request
    )


# Endpoint 5: Batch processing
@app.post("/batch/process")
async def batch_process(request: BatchProcessRequest):
    """
    Process multiple media items concurrently
    
    For each item:
    - If image: processes through /process/image
    - If video: processes through all 3 video endpoints (/process/video, /scene/index, /transcribe) concurrently
    
    Request body:
    {
        "media_items": [
            "9f9c443e-89c0-495c-b6f1-77ef30604b4a",
            "9f9c443e-89c0-495c-b6f1-77ef30604b4b"
        ],
        "prompt": "What's in this image?",
        "model": "google/gemini-2.0-flash-001",
        ...
    }
    """
    return await batch_process_endpoint(
        video_index=video_index,
        video_processor=video_processor,
        scene_indexer=scene_indexer,
        video_file_cache=video_file_cache,
        media_items=request.media_items,
        frame_prompt=request.prompt,
        model=request.model,
        granularity_seconds=request.granularity_seconds,
        scene_prompt=request.scene_prompt,
        extraction_type=request.extraction_type,
        threshold=request.threshold,
        frame_count=request.frame_count
    )


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Video Index API", "version": "2.0.0", "endpoints": 5}
