# Video Index API

FastAPI application for processing videos and images with LLM integration using OpenRouter.

## Project Structure

```
aidit/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── database.py              # SQLAlchemy models
│   ├── video_index.py           # VideoIndex class (LLM API calls)
│   ├── video_processor.py       # VideoProcessor class (video splitting)
│   └── video_index_processor.py # Queue management
├── docs/                         # Documentation
│   ├── README_API.md            # Original API documentation
│   └── README_VIDEO_API.md      # Video API documentation
├── examples/                     # Example scripts and old code
│   ├── wow.py                   # Original example script
│   ├── api.py                   # Original API implementation
│   └── chat_interface.html      # HTML interface
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
Create a `.env` file:
```
OPENROUTER_KEY=your-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
VIDEODB_API_KEY=your-videodb-api-key  # Optional, for scene indexing
```

3. **Initialize database tables:**
   - Option 1: Run the SQL in `schema.sql` in your Supabase SQL Editor
   - Option 2: Use the init script to check table status:
   ```bash
   uv run python init_db.py check
   ```

4. **Run the application:**
```bash
python run.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Image Processing
- `POST /process/image` - Process a single image from URL

### Video Processing
- `POST /process/video` - Process a video (downloads, splits, processes frames)
- `GET /status/{video_id}` - Get processing status
- `GET /status/{video_id}/frames` - Get all frames with results

### Error Detection
- `GET /detect/errors/{video_id}` - Detect and analyze errors
- `GET /detect/conflicts/{video_id}` - Detect conflicts and provide resolution

## Features

- ✅ Background processing with queue system
- ✅ Video splitting by granularity (seconds) using OpenCV
- ✅ Base64 conversion for efficient image transmission
- ✅ SQLAlchemy database tracking
- ✅ Configurable prompts per request
- ✅ Comprehensive logging
- ✅ Error detection and conflict resolution

## Documentation

See `docs/README_VIDEO_API.md` for detailed API documentation.

## Architecture

The application uses a modular architecture:

- **VideoIndex**: Handles LLM API calls (OpenRouter)
- **VideoProcessor**: Downloads and splits videos using OpenCV
- **VideoIndexProcessor**: Manages background queue and processing pipeline
- **Database**: SQLAlchemy models for tracking videos, frames, and logs

## Development

The application is organized as a Python package in the `app/` directory. All core functionality is modular and can be imported:

```python
from app.video_index import VideoIndex
from app.video_processor import VideoProcessor
from app.video_index_processor import VideoIndexProcessor
```

