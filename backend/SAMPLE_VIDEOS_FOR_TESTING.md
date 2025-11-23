# Sample Videos for LLM Quality Testing

## Recommended Test Videos

### 1. Educational/Tutorial Videos

**Why**: Test instructional content, step-by-step logic, concept explanations

#### Option A: Python Tutorial (Short)
- **Source**: YouTube
- **Link**: https://www.youtube.com/watch?v=kqtD5dpn9C8 (Python in 100 Seconds)
- **Duration**: ~2-3 minutes
- **Content**: Quick tutorial, clear structure
- **Test Scenarios**: `educational_short`, `tutorial_detailed`

#### Option B: Cooking Tutorial
- **Source**: YouTube
- **Link**: https://www.youtube.com/watch?v=Anxl3v1XXrE (Simple Recipe)
- **Duration**: ~5-10 minutes
- **Content**: Step-by-step instructions
- **Test Scenarios**: `tutorial_detailed`, `educational_short`

### 2. Vlog/Personal Content

**Why**: Test casual content, personality preservation, authentic moments

#### Option A: Daily Vlog
- **Source**: YouTube
- **Link**: https://www.youtube.com/watch?v=dQw4w9WgXcQ (Example vlog)
- **Duration**: ~10-15 minutes
- **Content**: Casual, personal, authentic
- **Test Scenarios**: `vlog_casual`, `minimal_prompt`

### 3. Long-Form Educational

**Why**: Test aggressive cutting, key moment extraction

#### Option A: Lecture/Webinar
- **Source**: YouTube
- **Link**: https://www.youtube.com/watch?v=example (30+ min lecture)
- **Duration**: 30-60 minutes
- **Content**: Long-form educational
- **Test Scenarios**: `very_long_video`, `educational_short`

### 4. Short Content

**Why**: Test minimal cutting, preservation logic

#### Option A: Quick Tips
- **Source**: YouTube
- **Link**: https://www.youtube.com/watch?v=example (1-2 min tips)
- **Duration**: 1-2 minutes
- **Content**: Quick, concise
- **Test Scenarios**: `very_short_video`, `minimal_prompt`

## Download Instructions

### Using `yt-dlp` (Recommended)

```bash
# Install yt-dlp
pip install yt-dlp

# Download video (best quality)
yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" <YOUTUBE_URL> -o "test_video_%(title)s.%(ext)s"

# Download with specific resolution
yt-dlp -f "best[height<=1080]" <YOUTUBE_URL> -o "test_video.%(ext)s"
```

### Using `youtube-dl` (Alternative)

```bash
# Install youtube-dl
pip install youtube-dl

# Download video
youtube-dl -f "best[ext=mp4]" <YOUTUBE_URL> -o "test_video.%(ext)s"
```

### Manual Download

1. Use browser extension (Video DownloadHelper, etc.)
2. Or use online tools (savefrom.net, etc.)
3. Ensure video is in MP4 format

## Upload to Database

After downloading, upload via the API:

```bash
# Using curl
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@test_video.mp4"

# Or use the frontend upload interface
```

## Test Video Requirements

### Minimum Requirements:
- **Format**: MP4 (H.264 video, AAC audio)
- **Resolution**: 720p or higher
- **Duration**: 
  - Short: 1-3 minutes
  - Medium: 5-15 minutes
  - Long: 30+ minutes
- **Audio**: Should have clear speech/audio
- **Content**: Should have some structure (not just random footage)

### Recommended Mix:
1. **1 short video** (1-3 min) - Quick tutorial
2. **1 medium video** (5-15 min) - Vlog or detailed tutorial
3. **1 long video** (30+ min) - Lecture or webinar

## Test Data Preparation

After uploading, ensure videos have:
- ✅ Transcription (run transcription task)
- ✅ Frame analysis (if available)
- ✅ Scene detection (if available)

```bash
# After upload, trigger processing
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze
```

## Alternative: Use Existing Videos

If you already have videos in the database:
1. Check available videos: `GET /api/videos/`
2. Use existing `video_id` for testing
3. Ensure they have transcription and analysis data

## Legal Note

⚠️ **Important**: Only download videos you have permission to use, or use videos with Creative Commons licenses. For testing purposes, consider:
- Your own videos
- Public domain content
- Creative Commons licensed content
- Videos with explicit permission

## Quick Test Setup

```bash
# 1. Download sample video
yt-dlp -f "best[height<=1080]" https://www.youtube.com/watch?v=EXAMPLE -o "test_educational.mp4"

# 2. Upload to database (via API or frontend)
# Get video_id from response

# 3. Trigger processing
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze

# 4. Wait for processing to complete

# 5. Run quality tests
python test_llm_quality.py {video_id}
```

