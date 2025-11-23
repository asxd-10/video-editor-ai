# EditorService Working & Performance

## How It Works

### **Current Flow (AI Edit)**

1. **User clicks "Apply AI Edit"** → Frontend calls `/api/videos/{video_id}/ai-edit/apply/{job_id}`
2. **Backend**:
   - Converts LLM EDL to EditorService format (removes transitions/skip segments)
   - Creates `EditJob` record with status `QUEUED`
   - Queues Celery task `apply_ai_edit_task` (non-blocking)
   - Returns immediately with `edit_job_id` and status `"queued"`
3. **Celery Worker** (background):
   - Processes `apply_ai_edit_task`
   - Updates `EditJob.status = PROCESSING`
   - Calls `EditorService.render_from_edl()` with EDL
   - Updates `EditJob.status = COMPLETED` with output paths
4. **Frontend**:
   - Polls `/api/videos/{video_id}/edit/{edit_job_id}` every 3-5 seconds
   - When status = `"completed"`, displays output video
   - User can download/view edited video

### **Rendering Process**

1. **Segment Extraction**: For each EDL segment:
   - FFmpeg extracts segment: `ffmpeg -ss {start} -i input.mp4 -t {duration} segment.mp4`
   - Applies aspect ratio conversion if needed
   - Saves to temp directory

2. **Concatenation**: 
   - Creates `concat.txt` file listing all segments
   - FFmpeg concatenates: `ffmpeg -f concat -i concat.txt -c copy output.mp4`
   - Adds captions if enabled
   - Normalizes audio if available

3. **Output**: Final MP4 saved to `../storage/processed/{video_id}/edited_{aspect}.mp4`

## Performance

### **Why It Takes Time**

1. **Segment Extraction**: Each segment = 1 FFmpeg call
   - 10 segments = 10 FFmpeg processes
   - Each process: decode → encode → write
   - **Time**: ~1-3 seconds per segment (depends on segment length)

2. **Concatenation**: Single FFmpeg call
   - Reads all segments
   - Merges streams
   - **Time**: ~2-5 seconds

3. **Total Time**: 
   - 10 segments: ~15-35 seconds
   - 30 segments: ~35-100 seconds
   - **This is expected** - video encoding is CPU-intensive

### **Optimization Opportunities**

1. **Parallel Segment Extraction** (Future):
   - Extract multiple segments concurrently
   - Could reduce time by 50-70%

2. **Hardware Acceleration**:
   - Use GPU encoding (`h264_nvenc`, `h264_qsv`)
   - Could reduce time by 60-80%

3. **Proxy Rendering**:
   - Render lower resolution first (for preview)
   - Then render full quality in background

4. **Caching**:
   - Cache segments if same EDL is re-rendered
   - Useful for re-rendering with different aspect ratios

## Background Processing

### **Yes, Uses Celery** ✅

- **AI Edit Rendering**: `apply_ai_edit_task` (Celery)
- **Regular Edit Rendering**: `create_edit_job_task` (Celery)
- **LLM Generation**: `generate_ai_edit_task` (Celery)

### **Why Background Processing?**

1. **Non-blocking**: API returns immediately
2. **Scalable**: Multiple workers can process jobs
3. **Resilient**: Retries on failure
4. **Progress Tracking**: Status updates in database

## Transitions

### **Current State: Not Implemented** ⚠️

**How it works now:**
- LLM generates EDL with `"type": "transition"` segments
- `EDLConverter` **skips** transition segments
- Segments are concatenated with **jump cuts** (no transitions)

**Example:**
```
LLM EDL: [
  {start: 0, end: 10, type: "keep"},
  {start: 10, end: 12, type: "transition", transition_type: "fade"},
  {start: 12, end: 20, type: "keep"}
]

After conversion: [
  {start: 0, end: 10, type: "keep"},
  {start: 12, end: 20, type: "keep"}
]

Result: Jump cut from 10s → 12s (no fade)
```

### **Future Implementation**

To add transitions, we need to:
1. Extract transition segments from LLM EDL
2. Apply FFmpeg filters between segments:
   - **Fade**: `fade=t=in:st=0:d=0.5` and `fade=t=out:st=X:d=0.5`
   - **Crossfade**: `xfade=transition=fade:duration=0.5`
   - **Zoom**: `zoompan=z='1.1':d=25`
3. Modify concatenation to include transition effects

**Note**: Transitions add complexity and rendering time. For MVP, jump cuts are acceptable.

## Frontend Display

### **Polling for Completion**

Frontend should:
1. Call `/api/videos/{video_id}/ai-edit/apply/{job_id}` → Gets `edit_job_id`
2. Poll `/api/videos/{video_id}/edit/{edit_job_id}` every 3-5 seconds
3. Check `status` field:
   - `"queued"` → Show "Rendering..."
   - `"processing"` → Show "Rendering..." with progress
   - `"completed"` → Show video player with output
   - `"failed"` → Show error message

### **Display Output**

When `status = "completed"`:
- `output_paths`: `{"16:9": "../storage/processed/.../edited_16_9.mp4", ...}`
- Convert relative path to URL: `/storage/processed/{video_id}/edited_{aspect}.mp4`
- Display video player for each aspect ratio
- Allow download

## Edge Cases Fixed

1. ✅ **Aspect Ratio Bug**: Fixed 1:1 cropping (now scales to fit larger dimension)
2. ✅ **Empty EDL**: Raises error
3. ✅ **Invalid Segments**: Validates start < end
4. ✅ **Out of Bounds**: Clips to video duration
5. ✅ **Very Small Segments**: Skips < 0.1s segments
6. ✅ **Overlapping Segments**: Auto-merges

## Performance Tips

1. **For Testing**: Use short videos (< 1 minute) or small EDLs (< 10 segments)
2. **For Production**: 
   - Use background processing (already implemented)
   - Show progress indicator
   - Allow user to close page (job continues in background)
3. **Monitor**: Check Celery worker logs for performance metrics

## Expected Rendering Times

| Video Length | Segments | Expected Time |
|--------------|----------|---------------|
| 1 min        | 5        | 10-20s        |
| 5 min        | 10       | 30-60s        |
| 10 min       | 20       | 60-120s       |
| 30 min       | 30       | 120-300s      |

*Times are approximate and depend on CPU, video resolution, and segment lengths*

