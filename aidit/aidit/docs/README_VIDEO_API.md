# Video Index API

FastAPI application for processing videos and images with LLM integration using OpenRouter.

## Architecture

The application consists of several key components:

### Core Classes

1. **VideoIndex** (`video_index.py`)
   - Handles API calls to LLM (OpenRouter)
   - Processes images from URLs or base64
   - Configurable prompts and models

2. **VideoProcessor** (`video_processor.py`)
   - Downloads videos from URLs
   - Splits videos into frames based on granularity (seconds)
   - Uses OpenCV for video processing
   - Converts frames to base64 for API transmission

3. **VideoIndexProcessor** (`video_index_processor.py`)
   - Manages background processing queue
   - Uses threading for concurrent processing
   - Handles video processing pipeline
   - Integrates with database for tracking

4. **Database Models** (`database.py`)
   - SQLAlchemy models for Video, Frame, and ProcessingLog
   - Tracks processing status, errors, and results
   - Stores LLM responses for each frame

### Main Application

**main.py** - FastAPI application with three main endpoints:

1. `/process/image` - Process single image from URL
2. `/process/video` - Process video (downloads, splits, processes frames)
3. `/status/{video_id}` - Get processing status
4. `/status/{video_id}/frames` - Get all frames with results
5. `/detect/errors/{video_id}` - Error detection and analysis
6. `/detect/conflicts/{video_id}` - Conflict detection and resolution

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export OPENROUTER_KEY="your-api-key-here"
# Optional: Set database URL (defaults to SQLite)
export DATABASE_URL="sqlite:///./video_processing.db"
```

Or create a `.env` file:
```
OPENROUTER_KEY=your-api-key-here
DATABASE_URL=sqlite:///./video_processing.db
```

3. Run the API server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST `/process/image`

Process a single image from URL.

**Request:**
```json
{
    "image_url": "https://example.com/image.jpg",
    "prompt": "What's in this image?",
    "model": "google/gemini-2.0-flash-001"
}
```

**Response:**
```json
{
    "success": true,
    "result": {
        "response": "The image shows...",
        "model": "google/gemini-2.0-flash-001",
        "usage": {...}
    },
    "image_url": "https://example.com/image.jpg"
}
```

### POST `/process/video`

Process a video by downloading, splitting into frames, and processing each frame.

**Request:**
```json
{
    "video_url": "https://example.com/video.mp4",
    "video_id": "optional-custom-id",
    "granularity_seconds": 1.0,
    "prompt": "What's in this image?",
    "model": "google/gemini-2.0-flash-001"
}
```

**Response:**
```json
{
    "success": true,
    "video_id": "video_abc123",
    "status": "queued",
    "message": "Video processing started. Use /status/{video_id} to check progress."
}
```

### GET `/status/{video_id}`

Get the processing status of a video.

**Response:**
```json
{
    "video_id": "video_abc123",
    "status": "processing",
    "total_frames": 100,
    "processed_frames": 45,
    "failed_frames": 2,
    "error_message": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:05:00"
}
```

### GET `/status/{video_id}/frames`

Get all frames with their processing results.

### GET `/detect/errors/{video_id}`

Detect and analyze errors in video processing.

### GET `/detect/conflicts/{video_id}`

Detect conflicts and provide resolution suggestions.

## Features

- **Background Processing**: Videos are processed asynchronously using a queue system
- **Frame-level Processing**: Each frame is processed individually with the LLM
- **Base64 Encoding**: Frames are converted to base64 for efficient API transmission
- **Database Tracking**: All processing status, errors, and results are logged
- **Error Detection**: Built-in error detection and conflict resolution
- **Configurable Prompts**: Custom prompts can be specified for each request
- **Granularity Control**: Control frame extraction interval (seconds)

## Database Schema

- **videos**: Stores video metadata and processing status
- **frames**: Stores individual frame data and LLM responses
- **processing_logs**: Stores detailed logs for debugging

## Logging

All operations are logged with timestamps and context. Logs are stored both in the database and in the application logs.

