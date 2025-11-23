# Upload Flow Test Checklist

## ✅ Backend-Frontend Sync Verification

### 1. Upload API Response Format
**Frontend expects:**
```javascript
{
  video_id: string,
  filename: string,
  status: string,
  file_size: number
}
```

**Backend returns:** ✅ Matches
- `video_id` ✅
- `filename` ✅
- `status` ✅ (string value from MediaStatus enum)
- `file_size` ✅

### 2. Get Video API Response Format
**Frontend expects:**
```javascript
{
  id: string,              // ✅ Backend returns: id: media.video_id
  title: string,
  filename: string,
  status: string,          // 'ready', 'processing', 'failed', etc.
  duration: number,
  duration_seconds: number,
  width: number,
  height: number,
  resolution: string,
  fps: number,
  aspect_ratio: string,
  has_audio: boolean,
  codec: string,
  video_codec: string,
  audio_codec: string,
  created_at: string,
  processing_started_at: string,
  processing_completed_at: string,
  assets: object,
  thumbnails: array,
  error: string,
  analysis_metadata: object,
  original_path: string,
  thumbnail: string
}
```

**Backend returns:** ✅ All fields present

### 3. List Videos API Response Format
**Frontend expects:**
```javascript
{
  total: number,
  skip: number,
  limit: number,
  videos: [{
    id: string,            // ✅ Backend returns: id: m.video_id
    title: string,
    filename: string,
    status: string,
    duration: number,
    created_at: string,
    thumbnail: string
  }]
}
```

**Backend returns:** ✅ Matches

## 🧪 Test Steps

### Step 1: Start Services
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload

# Terminal 2: Celery Worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Frontend
cd frontend
npm run dev
```

### Step 2: Test Upload Flow
1. Navigate to `http://localhost:5173/upload`
2. Select a video file (MP4, MOV, etc.)
3. Fill in title (optional: description)
4. Click "Start Upload"
5. **Verify:**
   - ✅ Upload progress shows
   - ✅ Status changes to "processing" after upload
   - ✅ Status polling works (checks every 2 seconds)
   - ✅ After processing completes, status changes to "ready"
   - ✅ Auto-navigates to `/video/{video_id}` after 2 seconds

### Step 3: Verify Database
```sql
-- Check media table
SELECT video_id, status, filename, file_size, duration_seconds 
FROM media 
ORDER BY created_at DESC 
LIMIT 1;

-- Check video_assets
SELECT video_id, asset_type, status 
FROM video_assets 
WHERE video_id = '<video_id>';

-- Check processing_logs
SELECT step, status, message 
FROM processing_logs 
WHERE video_id = '<video_id>' 
ORDER BY started_at;
```

### Step 4: Test Video View
1. After upload completes, verify video details page shows:
   - ✅ Video title
   - ✅ Status badge (should be "Ready")
   - ✅ Duration
   - ✅ Resolution
   - ✅ File size
   - ✅ Thumbnails (if generated)
   - ✅ Video player (if proxy created)

### Step 5: Test AI Story Editor Access
1. On video view page, verify:
   - ✅ "AI Story Editor" button appears when status is "ready"
2. Click button, navigate to `/video/{video_id}/ai-edit`
3. **Verify:**
   - ✅ Page loads without errors
   - ✅ Data loading works (media, transcription, frames, scenes)
   - ✅ Summary editor shows
   - ✅ Story prompt form shows

## 🐛 Potential Issues & Fixes

### Issue 1: Status Values Mismatch
- **Problem**: Frontend expects specific status strings
- **Expected**: 'pending', 'uploading', 'upload_complete', 'processing', 'ready', 'failed'
- **Backend**: Uses MediaStatus enum values ✅

### Issue 2: ID Field
- **Problem**: Frontend might expect `id` but backend returns `video_id`
- **Fix**: Backend returns `id: media.video_id` ✅

### Issue 3: Frames Query Bug
- **Problem**: `load_frames` was using wrong parameter
- **Fix**: ✅ Updated to use `video_id` (TEXT) instead of `media_id` (bigint)

## ✅ AI Story Editor Status

The AI Story Editor is **already compatible** with unified schema:
- ✅ Uses `DataLoader` which queries `media` table
- ✅ Fixed `load_frames` to use correct `video_id` parameter
- ✅ All queries use `video_id` (TEXT) from `media` table
- ✅ No changes needed to AI edit endpoints

## 📝 Next Steps After Testing

1. ✅ Verify upload flow works end-to-end
2. ✅ Test AI Story Editor with uploaded video
3. Update remaining services (if needed):
   - `app/api/edit.py` - Transcription, analysis, clip candidates
   - `app/services/editor.py` - Video editing
   - `app/services/transcription_service.py` - Transcription

