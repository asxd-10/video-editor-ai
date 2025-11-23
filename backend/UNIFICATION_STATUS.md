# Unification Status

## ✅ Completed

### 1. Schema Unification
- ✅ Created unified `media` table schema
- ✅ Created SQL migration script
- ✅ Schema ready in `migrations/schema/`

### 2. Model Alignment
- ✅ Created `Media` model (`app/models/media.py`)
- ✅ Created aidit models (`app/models/aidit_models.py`):
  - `VideoProcessing`, `Frame`, `SceneIndex`, `Transcription`
- ✅ Updated all foreign keys to reference `media.video_id`:
  - `VideoAsset`, `UploadChunk`, `ProcessingLog`
  - `Transcript`, `ClipCandidate`, `EditJob`
  - `RetentionAnalysis`, `AIEditJob`
- ✅ Updated `__init__.py` to export new models

### 3. Upload Unification
- ✅ Updated upload API (`app/api/upload.py`) to use `Media` model
- ✅ Updated processing task (`app/workers/tasks.py`) to use `Media` model
- ✅ All upload endpoints now use unified schema

## 🔄 In Progress

### Services Update
- Need to update other services that reference `Video`:
  - `app/services/editor.py`
  - `app/services/transcription_service.py`
  - `app/services/clip_selector.py`
  - `app/services/analysis_service.py`
  - `app/api/edit.py`
  - `app/api/ai_edit.py`

## 📋 Next Steps

1. **Update Remaining Services** - Migrate all services to use `Media`
2. **Test Upload Flow** - Verify complete upload → processing → ready flow
3. **Phase 3: Processing Integration** - Add frame/scene processing endpoints
4. **URL Upload Support** - Add support for URL-based uploads (aidit feature)

## 🎯 Current State

- **Database**: Unified schema ready
- **Models**: All aligned with unified schema
- **Upload API**: Using `Media` model
- **Processing**: Using `Media` model
- **Other APIs**: Still using `Video` (need migration)

## ⚠️ Breaking Changes

- API now returns `video_id` instead of `id` in responses
- All endpoints now query `Media` table instead of `videos`
- Frontend may need updates if it expects `id` field

