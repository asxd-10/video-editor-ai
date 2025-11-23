# Production Render Pipeline - Complete Guide

## Overview

This pipeline handles the complete production flow:
1. **Friend B's Pipeline**: Creates `sample_video_description.json` with frames, scenes, transcripts
2. **Friend A's Database**: Provides media records (S3 URLs) and frame records
3. **Our System**: Inserts data, generates edit plan, renders from S3 URLs

## Critical Feature: S3 URL Rendering

**FFmpeg can handle S3 URLs directly!** No need to download first.

The `EditorService` now:
- Uses `media.video_url` (S3 URL) if available, falls back to `media.original_path`
- Passes URL directly to FFmpeg (which supports HTTP/HTTPS URLs)
- Uses `http_persistent=1` for better performance with remote files

## Step-by-Step Process

### Step 1: Prepare Data Files

Create JSON files from production database:

**media_records.json**:
```json
[
  {
    "video_id": "b058ea09-d8bb-4b20-bba1-76fbdc97c929",
    "video_url": "https://ujertelpchurerutnjpp.supabase.co/storage/v1/object/public/videos/attachments/2025-11-23/1763877160468_ScreenRecording_11-22-2025_2-44-22_PM_1.MOV",
    "media_type": "video",
    "created_at": "2025-11-23 05:55:05.389707+00"
  }
]
```

**frame_records.json**:
```json
[
  {
    "video_id": 1,
    "frame_number": 0,
    "timestamp_seconds": 0,
    "llm_response": "Frame description...",
    "status": "completed"
  }
]
```

**sample_video_description.json**: Already provided by Friend B

### Step 2: Insert Production Data

```bash
python insert_production_data.py media_records.json frame_records.json sample_video_description.json
```

This will:
- Insert media records with S3 URLs
- Insert frames (from DB and/or JSON)
- Insert scenes (from JSON)
- Insert transcripts (from JSON `transcription_level_data`)

### Step 3: Test Render from S3

```bash
python test_production_render.py <video_id> story_prompt.json
```

This will:
- Load data from database
- Generate edit plan via LLM
- **Render edit directly from S3 URL** (no download needed!)

## Data Format Handling

### Transcript Format (transcription_level_data)

Friend B's format:
```json
{
  "transcript_text": "- Increase the age range - increase.",
  "transcript_data": [
    {"start": 0.0, "end": 0.08, "text": "-"},
    {"start": 0.08, "end": 0.24, "speaker": "A", "text": "Increase"},
    ...
  ],
  "segment_count": 7,
  "language_code": null
}
```

Our system:
- Inserts into `transcriptions` table (aidit format)
- Also inserts into `transcripts` table (our format) for EditorService
- Converts format: `{"start": float, "end": float, "text": str}`

### Frame Format

Friend B's format:
```json
{
  "frame_timestamp": 0,
  "description": "Frame description..."
}
```

Our system:
- Normalizes to: `timestamp_seconds`, `llm_response`
- Handles both formats automatically

### Scene Format

Friend B's format:
```json
{
  "scene_count": 1,
  "scenes": [
    {
      "start": 0.0,
      "end": 3.833,
      "description": "Scene description...",
      "metadata": {},
      "scene_metadata": {}
    }
  ]
}
```

Our system:
- Inserts into `scene_indexes` table
- Stores entire `scenes` array in `scenes_data` JSON column

## S3 URL Rendering

### How It Works

1. **EditorService** gets `video_url` from `Media` record
2. **FFmpeg** receives URL directly: `ffmpeg.input(video_url, ss=start_time)`
3. **FFmpeg** downloads segments on-the-fly (no full download needed)
4. **Rendering** happens as normal

### Performance

- **http_persistent=1**: Reuses HTTP connection for multiple segments
- **No local storage**: Videos stay in S3, only segments are downloaded temporarily
- **Efficient**: Only downloads segments needed for edit

### Example

```python
# Media record
video_url = "https://ujertelpchurerutnjpp.supabase.co/storage/v1/object/public/videos/attachments/2025-11-23/video.MOV"

# FFmpeg call
ffmpeg.input(video_url, ss=2.0, http_persistent="1")
# Downloads segment starting at 2.0s directly from S3
```

## Testing

### Quick Test

1. **Insert data**:
   ```bash
   python insert_production_data.py media_records.json frame_records.json sample_video_description.json
   ```

2. **Test render**:
   ```bash
   python test_production_render.py b058ea09-d8bb-4b20-bba1-76fbdc97c929 story_prompt.json
   ```

### Expected Output

```
✅ Edit plan generated in 25.0s
📊 Edit Statistics:
  Total 'keep' duration: 8.5s
  Coverage: 22.0%

✅ Video rendered in 45.0s
Output paths:
  16:9: /path/to/processed/b058ea09.../edited_16_9.mp4
  9:16: /path/to/processed/b058ea09.../edited_9_16.mp4
  1:1: /path/to/processed/b058ea09.../edited_1_1.mp4
```

## Troubleshooting

### Issue: "Video not found"
- **Fix**: Run `insert_production_data.py` first

### Issue: "Could not get duration from URL"
- **Fix**: Duration will be calculated from scenes/frames if available
- **Note**: FFmpeg probe may fail for some URLs, but rendering should still work

### Issue: FFmpeg errors with S3 URL
- **Check**: URL is publicly accessible
- **Check**: URL format is correct (https://...)
- **Note**: FFmpeg supports HTTP/HTTPS URLs natively

## Next Steps

1. **Test with real production data**
2. **Verify S3 URL rendering works**
3. **Optimize prompts based on results**
4. **Fine-tune coverage ranges if needed**

