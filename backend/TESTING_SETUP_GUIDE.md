# Testing Setup Guide - Fix Common Issues

## Issue 1: Missing Data (0 frames, 0 scenes, 0 transcript)

**Problem**: Video was just uploaded, processing hasn't completed yet.

**Solution**: Wait for processing to complete before testing.

```bash
# Option 1: Use helper script
python wait_for_processing.py {video_id} --trigger

# Option 2: Manual steps
# 1. Trigger transcription
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe

# 2. Trigger analysis
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze

# 3. Wait for processing (check status)
curl http://localhost:8000/api/videos/{video_id}/transcript/status

# 4. Once status is "complete", run tests
python test_llm_quality.py {video_id}
```

## Issue 2: Wrong Table Name (scenes vs scene_indexes)

**Problem**: Code was querying `scenes` table, but unified schema uses `scene_indexes`.

**Status**: ✅ **FIXED** - Updated `data_loader.py` to use `scene_indexes` table.

## Issue 3: Video Duration Seems Wrong

**Problem**: Video shows 3605.64s (~60 min) but should be shorter.

**Possible Causes**:
1. Video file is actually that long
2. Metadata extraction is incorrect
3. File corruption

**Check**:
```bash
# Check actual video duration with ffprobe
ffprobe -i test_videos/educational_short.mp4 -show_entries format=duration -v quiet -of csv="p=0"
```

**Fix**: If duration is wrong, re-upload the video or check the file.

## Complete Testing Workflow

### Step 1: Upload Video
```bash
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@test_videos/educational_short.mp4"
```

### Step 2: Wait for Processing
```bash
# Get video_id from upload response, then:
python wait_for_processing.py {video_id} --trigger
```

This will:
- Trigger transcription if not started
- Trigger analysis if not started
- Wait for processing to complete
- Show status updates every 5 seconds

### Step 3: Verify Data
```bash
# Check what data is available
python -c "
from app.database import SessionLocal
from app.models.media import Media
from app.models.aidit_models import Transcription, SceneIndex, Frame

db = SessionLocal()
media = db.query(Media).filter(Media.video_id == '{video_id}').first()
print(f'Duration: {media.duration_seconds}s')
print(f'Status: {media.status}')

trans = db.query(Transcription).filter(Transcription.video_id == '{video_id}').first()
print(f'Transcription: {trans.status if trans else \"None\"} ({len(trans.transcript_data) if trans and trans.transcript_data else 0} segments)')

scenes = db.query(SceneIndex).filter(SceneIndex.video_id == '{video_id}').first()
print(f'Scenes: {scenes.status if scenes else \"None\"} ({scenes.scene_count if scenes else 0} scenes)')

frames = db.query(Frame).filter(Frame.video_id == '{video_id}').count()
print(f'Frames: {frames}')
"
```

### Step 4: Run Tests
```bash
# Once processing is complete:
python test_llm_quality.py {video_id}
```

## Expected Processing Times

- **Transcription**: 1-5 minutes (depends on video length)
- **Analysis**: 2-10 minutes (depends on video length and complexity)
- **Frame indexing**: 5-30 minutes (if enabled, depends on video length)

## Troubleshooting

### Processing Stuck?
1. Check Celery worker logs
2. Check database for error messages
3. Check `processing_logs` table for errors

### No Transcription?
1. Check Celery worker is running: `celery -A app.workers.celery_app worker --loglevel=info`
2. Check transcription task status
3. Check for errors in `transcriptions` table

### No Scenes/Frames?
1. These are optional - LLM can work with just transcription
2. If needed, check if scene detection is enabled
3. Check `scene_indexes` and `frames` tables

## Quick Test (Minimal Data)

If you just want to test LLM quality without waiting for all processing:

```python
# The LLM can work with just transcription
# So you can test with:
# - ✅ Transcription (required)
# - ❌ Scenes (optional)
# - ❌ Frames (optional)

# Minimum viable test:
# 1. Upload video
# 2. Wait for transcription only
# 3. Run tests (will work, but quality may be lower)
```

## Next Steps

1. ✅ Fix table name issue (done)
2. ⏳ Wait for processing to complete
3. ✅ Run quality tests
4. 📊 Review results and fine-tune prompts

