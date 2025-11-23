# Model Alignment Analysis

## Current State vs Unified Schema

### ✅ Schema Created
- Unified schema SQL file exists (should be in `migrations/schema/`)
- Database structure defined with `media` as core table

### ❌ Models Need Updates

#### 1. **Missing: Media Model**
- **Current:** `Video` model uses `videos` table
- **Required:** `Media` model using `media` table
- **Action:** Create new `Media` model aligned with unified schema

#### 2. **Foreign Key Updates Needed**
All models currently reference `videos.id` but should reference `media.video_id`:

- ✅ `AIEditJob` - Already uses `video_id` (no FK, correct)
- ❌ `VideoAsset` - References `videos.id` → needs `media.video_id`
- ❌ `UploadChunk` - References `videos.id` → needs `media.video_id`
- ❌ `ProcessingLog` - References `videos.id` → needs `media.video_id`
- ❌ `Transcript` - References `videos.id` → needs `media.video_id`
- ❌ `ClipCandidate` - References `videos.id` → needs `media.video_id`
- ❌ `EditJob` - References `videos.id` → needs `media.video_id`
- ❌ `RetentionAnalysis` - References `videos.id` → needs `media.video_id`

#### 3. **Missing: Aidit Models**
Need to create models for new tables:
- ❌ `VideoProcessing` - Frame processing status
- ❌ `Frame` - Frame-level data with LLM responses
- ❌ `SceneIndex` - Scene extraction results
- ❌ `Transcription` - Unified transcription (different from `Transcript`)

#### 4. **Table Name Mismatches**
- `transcripts` table → should be `transcriptions` (unified schema)
- Need to decide: keep `Transcript` model or create `Transcription`?

## Migration Strategy

### Option A: Dual Support (Recommended)
1. Create `Media` model
2. Keep `Video` model temporarily (for backward compatibility)
3. Update all foreign keys to `media.video_id`
4. Create new aidit models
5. Gradually migrate code to use `Media` instead of `Video`

### Option B: Direct Migration
1. Rename `Video` → `Media`
2. Update all references immediately
3. More disruptive but cleaner

## Next Steps

1. ✅ Create `Media` model
2. ✅ Create aidit models (`VideoProcessing`, `Frame`, `SceneIndex`, `Transcription`)
3. ✅ Update foreign keys in all models
4. ✅ Update relationships
5. ✅ Test model queries
6. ✅ Update API endpoints to use `Media`
7. ✅ Phase 2: Upload Unification

