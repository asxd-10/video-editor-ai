# Upload Flow Testing Guide

## Frontend Expectations

### Upload Response (`POST /api/videos/`)
Frontend expects:
```javascript
{
  video_id: string,      // ✅ Backend returns this
  filename: string,      // ✅ Backend returns this
  status: string,        // ✅ Backend returns this
  file_size: number      // ✅ Backend returns this
}
```

### Get Video Response (`GET /api/videos/{video_id}`)
Frontend expects:
```javascript
{
  id: string,            // ✅ Backend returns id: media.video_id
  title: string,
  filename: string,
  status: string,       // 'ready', 'processing', 'failed', etc.
  file_size: number,
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

### List Videos Response (`GET /api/videos/`)
Frontend expects:
```javascript
{
  total: number,
  skip: number,
  limit: number,
  videos: [
    {
      id: string,         // ✅ Backend returns id: m.video_id
      title: string,
      filename: string,
      status: string,
      duration: number,
      created_at: string,
      thumbnail: string
    }
  ]
}
```

## Testing Steps

1. **Start Backend**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Upload Flow**
   - Navigate to `/upload`
   - Select a video file
   - Fill in title/description (optional)
   - Click upload
   - Verify:
     - ✅ Upload progress shows
     - ✅ Status changes to "processing"
     - ✅ After processing, status changes to "ready"
     - ✅ Auto-navigates to `/video/{video_id}`

4. **Verify Database**
   - Check `media` table has new record
   - Check `video_assets` table has proxy/thumbnails
   - Check `processing_logs` table has logs

5. **Test Video View**
   - Verify video details display correctly
   - Verify thumbnails show
   - Verify status is "ready"

## Potential Issues

### Issue 1: Status Mismatch
- **Problem**: Frontend expects enum values, backend returns string
- **Fix**: Backend already returns string (MediaStatus.value)

### Issue 2: ID Field
- **Problem**: Frontend might expect `id` but backend returns `video_id`
- **Fix**: Backend returns `id: media.video_id` ✅

### Issue 3: Status Values
- **Problem**: Status values might differ
- **Expected**: 'pending', 'uploading', 'upload_complete', 'processing', 'ready', 'failed'
- **Backend**: Uses MediaStatus enum values ✅

## Checklist

- [ ] Upload creates Media record
- [ ] Processing task updates Media record
- [ ] Frontend receives correct response format
- [ ] Status polling works
- [ ] Video view displays correctly
- [ ] Thumbnails load correctly
- [ ] All fields match frontend expectations

