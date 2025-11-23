# Next Steps After Schema Unification

## ✅ Completed
1. **Schema Unification** - Created unified `media` table schema
2. **Schema Scripts** - Created migration scripts in `migrations/schema/`
3. **Model Analysis** - Analyzed current models vs unified schema

## 🔄 In Progress
1. **Model Alignment** - Creating Media model and aidit models

## 📋 Immediate Next Steps

### Step 1: Complete Model Alignment (Current Task)
- [x] Create `Media` model (`app/models/media.py`)
- [ ] Create aidit models (`app/models/aidit_models.py`)
- [ ] Update all existing models to reference `media.video_id`:
  - [ ] `VideoAsset` - Change FK from `videos.id` → `media.video_id`
  - [ ] `UploadChunk` - Change FK from `videos.id` → `media.video_id`
  - [ ] `ProcessingLog` - Change FK from `videos.id` → `media.video_id`
  - [ ] `Transcript` - Change FK from `videos.id` → `media.video_id`
  - [ ] `ClipCandidate` - Change FK from `videos.id` → `media.video_id`
  - [ ] `EditJob` - Change FK from `videos.id` → `media.video_id`
  - [ ] `RetentionAnalysis` - Change FK from `videos.id` → `media.video_id`
  - [ ] `AIEditJob` - Already correct (no FK, uses `video_id`)
- [ ] Update `__init__.py` to export new models
- [ ] Test model queries

### Step 2: Phase 2 - Upload Unification
According to `INTEGRATION_ANALYSIS.md`, Phase 2 includes:

1. **Create Unified Upload Service**
   - Support both file uploads (current) and URL uploads (aidit)
   - Location: `app/services/media/upload_service.py`
   - Features:
     - File upload with chunking
     - URL-based upload
     - Automatic media type detection
     - Create `Media` record (not `Video`)

2. **Update API Endpoints**
   - `POST /api/videos/upload` - Support both file and URL
   - Update to use `Media` model instead of `Video`
   - Return `media.video_id` instead of `videos.id`

3. **Storage Service Updates**
   - Handle both local file storage and URL references
   - Update `StorageService` to work with `Media`

### Step 3: Phase 3 - Processing Integration
1. **Frame Processing Integration**
   - Integrate aidit's frame extraction and LLM processing
   - Create `POST /api/videos/{video_id}/process/frames` endpoint
   - Use `VideoProcessing` and `Frame` models

2. **Scene Indexing Integration**
   - Integrate aidit's scene indexing (videodb)
   - Create `POST /api/videos/{video_id}/process/scenes` endpoint
   - Use `SceneIndex` model

3. **Transcription Unification**
   - Support both videodb (aidit) and faster-whisper (current)
   - Use `Transcription` model (unified) instead of `Transcript`
   - Update transcription endpoints

## 🎯 Priority Order

1. **NOW**: Complete model alignment (Step 1)
2. **NEXT**: Upload unification (Step 2) - Most critical for new uploads
3. **THEN**: Processing integration (Step 3) - Adds new features

## 📝 Notes

- Keep `Video` model temporarily for backward compatibility
- Gradually migrate code from `Video` → `Media`
- All new code should use `Media` model
- Test each step before moving to next

## 🔍 Key Files to Update

### Models
- `app/models/__init__.py` - Export new models
- `app/models/video.py` - Keep for now, add deprecation notice
- `app/models/media.py` - ✅ Created
- `app/models/aidit_models.py` - ✅ Created
- All other models - Update foreign keys

### Services
- `app/services/storage_service.py` - Update to use Media
- `app/services/media/upload_service.py` - Create new unified service

### API
- `app/api/upload.py` - Update to use Media and unified upload
- All endpoints using `Video` - Gradually migrate to `Media`

