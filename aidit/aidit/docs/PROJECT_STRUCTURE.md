# Project Structure

This document describes the organization of the Video Index API project.

## Directory Structure

```
aidit/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application and endpoints
│   ├── database.py              # SQLAlchemy models and database setup
│   ├── video_index.py           # VideoIndex class for LLM API calls
│   ├── video_processor.py       # VideoProcessor for video splitting
│   └── video_index_processor.py # Queue management and background processing
│
├── docs/                         # Documentation
│   ├── README_API.md            # Original API documentation
│   ├── README_VIDEO_API.md      # Video API documentation
│   └── PROJECT_STRUCTURE.md     # This file
│
├── examples/                     # Example scripts and legacy code
│   ├── wow.py                   # Original example script
│   ├── api.py                   # Original API implementation
│   └── chat_interface.html      # HTML chat interface
│
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # Main project README
```

## Module Descriptions

### app/main.py
FastAPI application with three main endpoint groups:
- Image processing (`/process/image`)
- Video processing (`/process/video`, `/status/{video_id}`)
- Error detection (`/detect/errors/{video_id}`, `/detect/conflicts/{video_id}`)

### app/database.py
SQLAlchemy models:
- `Video`: Video metadata and processing status
- `Frame`: Individual frame data and LLM responses
- `ProcessingLog`: Detailed processing logs
- Database initialization functions

### app/video_index.py
`VideoIndex` class:
- Handles API calls to OpenRouter LLM
- Processes images from URLs or base64
- Configurable prompts and models

### app/video_processor.py
`VideoProcessor` class:
- Downloads videos from URLs
- Splits videos into frames using OpenCV
- Converts frames to base64 for API transmission

### app/video_index_processor.py
`VideoIndexProcessor` class:
- Manages background processing queue
- Uses threading for concurrent processing
- Integrates with database for tracking
- Handles complete video processing pipeline

## Running the Application

### Option 1: Using run.py
```bash
python run.py
```

### Option 2: Using uvicorn directly
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Import Structure

All application modules use relative imports within the `app` package:

```python
from .database import Video, Frame
from .video_index import VideoIndex
from .video_processor import VideoProcessor
from .video_index_processor import VideoIndexProcessor
```

## File Organization Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Package Structure**: Core application code in `app/` package
3. **Documentation**: All docs in `docs/` directory
4. **Examples**: Legacy and example code in `examples/` directory
5. **Configuration**: Environment variables and config at root level



