# Codebase Integration Analysis
## Video Editor AI + Aidit Integration Plan

**Date:** 2025-11-22  
**Purpose:** Comprehensive analysis of both codebases to create unified, centralized architecture

---

## Executive Summary

This document analyzes two video processing codebases:
1. **Current Codebase** (`backend/`): Video upload platform with editing, transcription, analysis, and AI storytelling
2. **Aidit Codebase** (`aidit/aidit/`): Video indexing system with frame-level LLM processing, scene indexing, and transcription

**Goal:** Create a unified video ingestion and processing framework that:
- Centralizes database schema
- Unifies upload logic
- Standardizes processing pipelines
- Preserves all features while improving speed and accuracy
- Enables both use cases (editing + indexing)

---

## 1. Database Schema Comparison

### 1.1 Aidit Schema (`aidit/aidit/schema.sql`)

**Tables:**
- `media` - Core media metadata (video_id, video_url, media_type)
- `video_processing` - Frame processing status (granularity, prompt, model, frame counts)
- `image_processing` - Single image processing results
- `frames` - Frame-level data (frame_number, timestamp, llm_response, status)
- `scene_indexes` - Scene extraction results (index_id, scenes_data JSONB)
- `transcriptions` - Transcription data (transcript_data JSONB, transcript_text)
- `processing_logs` - Processing audit trail

**Key Characteristics:**
- Uses `video_id` (TEXT) as primary identifier
- `frames.video_id` references `media.id` (BIGINT foreign key)
- JSONB for complex data (scenes_data, transcript_data)
- Status tracking at multiple levels (video_processing, frames)

### 1.2 Current Schema (`backend/app/models/`)

**Tables:**
- `videos` - Comprehensive video metadata (file info, technical specs, status)
- `video_assets` - Derived assets (proxy, thumbnails)
- `upload_chunks` - Chunked upload tracking
- `processing_logs` - Processing audit trail
- `transcripts` - Transcription data (SQLAlchemy model)
- `clip_candidates` - AI-generated clip suggestions
- `edit_jobs` - Video editing jobs
- `retention_analysis` - Retention curve analysis
- `ai_edit_jobs` - AI storytelling edit jobs

**Key Characteristics:**
- Uses `id` (UUID string) as primary identifier
- File-based storage paths
- Enum-based status tracking
- Relationships via SQLAlchemy ORM

### 1.3 Schema Unification Strategy

**Proposed Unified Schema:**

```sql
-- Core Media Table (unified)
CREATE TABLE media (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,  -- UUID from current, or custom from aidit
    video_url TEXT,                  -- URL (aidit) or file path (current)
    media_type TEXT NOT NULL DEFAULT 'video',
    
    -- File metadata (from current)
    filename TEXT,
    original_filename TEXT,
    file_extension TEXT,
    mime_type TEXT,
    file_size BIGINT,
    checksum_md5 TEXT,
    original_path TEXT,              -- File path (current) or URL (aidit)
    
    -- Technical metadata (from current)
    duration_seconds FLOAT,
    fps FLOAT,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    bitrate_kbps INTEGER,
    has_audio BOOLEAN,
    aspect_ratio TEXT,
    
    -- Status (unified)
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    -- User metadata (from current)
    uploaded_by TEXT,
    title TEXT,
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Video Processing (from aidit, enhanced)
CREATE TABLE video_processing (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    status TEXT NOT NULL DEFAULT 'pending',
    processing_type TEXT NOT NULL,  -- 'frame_indexing', 'scene_indexing', 'transcription', 'analysis'
    granularity_seconds FLOAT,
    prompt TEXT,
    model TEXT,
    total_frames INTEGER DEFAULT 0,
    processed_frames INTEGER DEFAULT 0,
    failed_frames INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Frames (from aidit, enhanced)
CREATE TABLE frames (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    frame_number INTEGER NOT NULL,
    timestamp_seconds FLOAT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    llm_response TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, frame_number)
);

-- Scene Indexes (from aidit)
CREATE TABLE scene_indexes (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    video_db_id TEXT,  -- videodb ID
    index_id TEXT NOT NULL,
    extraction_type TEXT NOT NULL DEFAULT 'shot_based',
    prompt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    scene_count INTEGER DEFAULT 0,
    scenes_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, index_id)
);

-- Transcriptions (unified from both)
CREATE TABLE transcriptions (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    video_db_id TEXT,  -- videodb ID (aidit)
    language_code TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    transcript_data JSONB,  -- Full segment data
    transcript_text TEXT,   -- Plain text version
    segment_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id)  -- One transcription per video
);

-- Video Assets (from current)
CREATE TABLE video_assets (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    asset_type TEXT NOT NULL,  -- 'proxy_720p', 'thumbnail', etc.
    file_path TEXT NOT NULL,
    file_size BIGINT,
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Processing Logs (unified)
CREATE TABLE processing_logs (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES media(video_id),
    frame_id BIGINT REFERENCES frames(id),
    level TEXT NOT NULL,  -- 'INFO', 'WARNING', 'ERROR'
    step TEXT,             -- Processing step name
    message TEXT NOT NULL,
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Additional tables from current (preserved)
CREATE TABLE upload_chunks (...);
CREATE TABLE clip_candidates (...);
CREATE TABLE edit_jobs (...);
CREATE TABLE retention_analysis (...);
CREATE TABLE ai_edit_jobs (...);
```

**Migration Strategy:**
1. Create unified `media` table with all fields
2. Migrate `videos` → `media` (map `videos.id` → `media.video_id`)
3. Migrate aidit `media` → unified `media`
4. Update foreign keys in dependent tables
5. Create views/aliases for backward compatibility during transition

---

## 2. Upload Flow Comparison

### 2.1 Current Upload Flow

**Endpoint:** `POST /api/videos/` or `POST /api/videos/chunk`

**Process:**
1. Receive file upload (single or chunked)
2. Validate file (extension, MIME type, size)
3. Save to storage (`storage/uploads/{video_id}/`)
4. Create `Video` record with status `UPLOAD_COMPLETE`
5. Trigger Celery task `process_video_task`
6. Task extracts metadata, creates proxy, thumbnails
7. Update status to `READY`

**Features:**
- Chunked upload support
- File validation
- MD5 checksum
- Storage path management
- Background processing via Celery

### 2.2 Aidit Upload Flow

**Endpoint:** `POST /process/video` or `POST /batch/process`

**Process:**
1. Receive `video_url` (HTTP/HTTPS/S3)
2. Create `media` record
3. Create `video_processing` record
4. Download video (temporary)
5. Split into frames by granularity
6. Process frames concurrently (LLM calls)
7. Save frame data to database
8. Clean up temporary file

**Features:**
- URL-based uploads
- Frame extraction with configurable granularity
- Concurrent frame processing
- LLM integration per frame

### 2.3 Unified Upload Flow

**Proposed Unified Endpoint:** `POST /api/videos/upload`

**Request Types:**
1. **File Upload** (current):
   ```json
   {
     "type": "file",
     "file": <multipart>,
     "title": "...",
     "description": "..."
   }
   ```

2. **URL Upload** (aidit):
   ```json
   {
     "type": "url",
     "video_url": "https://...",
     "video_id": "optional-uuid",
     "title": "..."
   }
   ```

**Unified Process:**
```
1. Validate request (file or URL)
2. Generate/use video_id (UUID)
3. Create media record (unified schema)
4. If file:
   - Save to storage
   - Set original_path = file path
   - Set video_url = null
5. If URL:
   - Set video_url = URL
   - Set original_path = null (or download path)
6. Trigger unified processing pipeline
7. Return video_id and status
```

**Processing Pipeline (Unified):**
```
process_video_pipeline(video_id):
  1. Extract metadata (FFmpeg) - from current
  2. Create proxy video (FFmpeg) - from current
  3. Extract thumbnails (FFmpeg) - from current
  4. Optional: Frame indexing (OpenCV + LLM) - from aidit
  5. Optional: Scene indexing (videodb) - from aidit
  6. Optional: Transcription (videodb or Whisper) - from both
  7. Update status to READY
```

---

## 3. Processing Logic Comparison

### 3.1 Video Processing

**Current (`backend/app/services/video_processor.py`):**
- Uses **FFmpeg** (`ffmpeg-python`)
- Extracts metadata (duration, fps, codecs, etc.)
- Creates proxy videos (720p, optimized)
- Extracts thumbnails (evenly spaced)
- File-based operations

**Aidit (`aidit/aidit/app/video_processor.py`):**
- Uses **OpenCV** (`cv2`)
- Downloads videos from URLs
- Splits into frames by granularity (seconds)
- Converts frames to base64
- Temporary file management

**Unified Approach:**
- **Primary:** FFmpeg for metadata, proxy, thumbnails (more efficient, better quality)
- **Secondary:** OpenCV for frame extraction when needed (for LLM processing)
- **Hybrid:** Use FFmpeg for most operations, OpenCV only for frame-level LLM indexing

### 3.2 Frame Processing

**Aidit (`aidit/aidit/app/video_index.py`):**
- Calls OpenRouter LLM API with base64 images
- Processes frames concurrently using `asyncio`
- Saves LLM responses to `frames` table
- Configurable prompts and models

**Current:**
- No frame-level processing (only video-level)

**Unified Approach:**
- Integrate aidit's frame processing as optional step
- Trigger frame indexing via separate endpoint or flag
- Use existing LLM client infrastructure

### 3.3 Scene Indexing

**Aidit (`aidit/aidit/app/scene_indexer.py`):**
- Uses **videodb** API for scene extraction
- Supports shot-based and time-based extraction
- Uploads video to videodb
- Polls for scene index results
- Saves to `scene_indexes` table

**Current:**
- No scene indexing (only scene detection via scenedetect)

**Unified Approach:**
- Use videodb for cloud-based scene indexing (aidit)
- Keep scenedetect for local scene detection (current)
- Allow both methods, choose based on configuration

### 3.4 Transcription

**Aidit:**
- Uses **videodb** `index_spoken_words()` API
- Polls for transcript
- Saves to `transcriptions` table

**Current:**
- Uses **faster-whisper** (local)
- Saves to `transcripts` table
- Celery task for background processing

**Unified Approach:**
- Support both methods:
  - **videodb** (cloud, faster, requires API key)
  - **faster-whisper** (local, no API key, slower)
- Choose based on configuration or availability
- Unified `transcriptions` table schema

---

## 4. API Endpoint Comparison

### 4.1 Current Endpoints

```
POST   /api/videos/              - Upload video (file)
POST   /api/videos/chunk         - Upload chunk
GET    /api/videos/              - List videos
GET    /api/videos/{video_id}    - Get video details
GET    /api/videos/{video_id}/logs - Get logs
DELETE /api/videos/{video_id}    - Delete video

POST   /api/videos/{video_id}/transcribe - Start transcription
GET    /api/videos/{video_id}/transcript - Get transcript
POST   /api/videos/{video_id}/analyze    - Start analysis
GET    /api/videos/{video_id}/candidates - Get clip candidates
POST   /api/videos/{video_id}/candidates - Generate candidates
POST   /api/videos/{video_id}/edit       - Create edit job
GET    /api/videos/{video_id}/edit       - List edit jobs

POST   /api/videos/{video_id}/ai-edit/generate - Generate AI edit
GET    /api/videos/{video_id}/ai-edit/plan/{job_id} - Get AI edit plan
POST   /api/videos/{video_id}/ai-edit/apply/{job_id} - Apply AI edit
```

### 4.2 Aidit Endpoints

```
POST   /process/image            - Process single image
POST   /process/video            - Process video frames
POST   /scene/index              - Scene indexing
POST   /transcribe               - Transcription
POST   /batch/process            - Batch processing
```

### 4.3 Unified Endpoint Structure

```
# Upload & Media Management
POST   /api/videos/upload        - Unified upload (file or URL)
GET    /api/videos/              - List videos
GET    /api/videos/{video_id}    - Get video details
DELETE /api/videos/{video_id}    - Delete video

# Processing
POST   /api/videos/{video_id}/process/frames      - Frame indexing (aidit)
GET    /api/videos/{video_id}/frames              - Get frames
POST   /api/videos/{video_id}/process/scenes     - Scene indexing (aidit)
GET    /api/videos/{video_id}/scenes            - Get scenes
POST   /api/videos/{video_id}/transcribe         - Transcription (unified)
GET    /api/videos/{video_id}/transcript         - Get transcript

# Analysis & Editing (current)
POST   /api/videos/{video_id}/analyze            - Start analysis
GET    /api/videos/{video_id}/candidates         - Get clip candidates
POST   /api/videos/{video_id}/candidates         - Generate candidates
POST   /api/videos/{video_id}/edit               - Create edit job
GET    /api/videos/{video_id}/edit               - List edit jobs

# AI Editing (current)
POST   /api/videos/{video_id}/ai-edit/generate   - Generate AI edit
GET    /api/videos/{video_id}/ai-edit/plan/{job_id} - Get AI edit plan
POST   /api/videos/{video_id}/ai-edit/apply/{job_id} - Apply AI edit

# Batch Processing (aidit)
POST   /api/videos/batch/process                - Batch process multiple videos
```

---

## 5. Service Layer Comparison

### 5.1 Current Services

- `VideoProcessor` - FFmpeg operations (metadata, proxy, thumbnails)
- `StorageService` - File storage management
- `TranscriptionService` - faster-whisper integration
- `AnalysisService` - Silence detection, scene detection
- `ClipSelector` - AI clip selection
- `EditorService` - Video editing operations
- `AI Services` - Storytelling agent, LLM client, data compression

### 5.2 Aidit Services

- `VideoProcessor` - OpenCV frame extraction
- `VideoIndex` - LLM API calls (OpenRouter)
- `SceneIndexer` - videodb integration
- `Database` - Supabase operations

### 5.3 Unified Service Architecture

```
app/services/
├── media/
│   ├── upload_service.py        - Unified upload (file + URL)
│   └── storage_service.py       - File storage (current)
├── processing/
│   ├── video_processor.py       - FFmpeg operations (current)
│   ├── frame_processor.py      - OpenCV frame extraction (aidit)
│   ├── metadata_extractor.py   - Video metadata (current)
│   └── asset_generator.py      - Proxy, thumbnails (current)
├── indexing/
│   ├── frame_indexer.py         - Frame-level LLM processing (aidit)
│   ├── scene_indexer.py         - Scene indexing (aidit + current)
│   └── transcription_service.py - Unified transcription (both)
├── analysis/
│   ├── analysis_service.py      - Silence, scene detection (current)
│   └── clip_selector.py         - AI clip selection (current)
├── editing/
│   ├── editor_service.py        - Video editing (current)
│   └── ai_editor_service.py     - AI storytelling (current)
└── llm/
    ├── llm_client.py            - Unified LLM client (both)
    └── video_index.py           - Frame processing (aidit)
```

---

## 6. Task Queue Comparison

### 6.1 Current

- **Celery** with Redis
- Tasks: `process_video_task`, `transcribe_video_task`, `analyze_video_task`, `create_edit_job_task`, `generate_ai_edit_task`
- Async processing for long-running operations

### 6.2 Aidit

- **Threading** (`VideoIndexProcessor`)
- In-process queue management
- Synchronous processing with async LLM calls

### 6.3 Unified Approach

- **Primary:** Celery (current) - better for production, scalability
- **Fallback:** Threading for simple operations
- All long-running tasks use Celery
- Frame processing can be batched in Celery tasks

---

## 7. Integration Plan

### Phase 1: Schema Unification (Week 1)

1. Create unified `media` table migration
2. Migrate current `videos` → `media`
3. Migrate aidit `media` → unified `media`
4. Update foreign keys
5. Create compatibility views

### Phase 2: Upload Unification (Week 1-2)

1. Create unified upload service
2. Support both file and URL uploads
3. Update API endpoints
4. Test both upload methods

### Phase 3: Processing Integration (Week 2-3)

1. Integrate frame processing (aidit) as optional step
2. Integrate scene indexing (aidit) as alternative to scenedetect
3. Unify transcription (support both videodb and faster-whisper)
4. Update processing pipeline

### Phase 4: Service Layer Refactoring (Week 3-4)

1. Reorganize services into unified structure
2. Create shared utilities
3. Update all endpoints to use unified services
4. Comprehensive testing

### Phase 5: Frontend Integration (Week 4)

1. Update frontend to support new endpoints
2. Add UI for frame indexing
3. Add UI for scene indexing
4. Test end-to-end flows

---

## 8. Key Decisions

### 8.1 Database

- **Decision:** Use unified `media` table as source of truth
- **Rationale:** Single source of truth, easier to maintain, supports both use cases

### 8.2 Upload Method

- **Decision:** Support both file and URL uploads
- **Rationale:** Current needs file uploads, aidit needs URL uploads

### 8.3 Video Processing

- **Decision:** FFmpeg primary, OpenCV secondary
- **Rationale:** FFmpeg better for metadata/proxy, OpenCV only needed for frame extraction

### 8.4 Transcription

- **Decision:** Support both videodb and faster-whisper
- **Rationale:** videodb faster/cloud, faster-whisper local/no API key

### 8.5 Task Queue

- **Decision:** Celery primary, threading fallback
- **Rationale:** Celery better for production, threading for simple operations

### 8.6 Scene Indexing

- **Decision:** Support both videodb and scenedetect
- **Rationale:** videodb cloud-based, scenedetect local

---

## 9. Risk Assessment

### High Risk
- **Schema migration:** Data loss if not careful
- **Breaking changes:** Existing code may break
- **Performance:** Unified system may be slower initially

### Medium Risk
- **API compatibility:** Frontend may need updates
- **Testing:** Complex integration requires thorough testing
- **Documentation:** Need to update all docs

### Low Risk
- **Feature loss:** All features preserved
- **Deployment:** Can deploy incrementally

---

## 10. Success Criteria

1. ✅ All features from both codebases work
2. ✅ Unified upload supports both file and URL
3. ✅ Unified schema with no data loss
4. ✅ Processing pipeline supports all operations
5. ✅ Performance equal or better than before
6. ✅ Frontend works with unified backend
7. ✅ Comprehensive test coverage
8. ✅ Documentation updated

---

## Next Steps

1. Review this analysis with team
2. Approve integration plan
3. Start Phase 1 (Schema Unification)
4. Create detailed migration scripts
5. Set up testing environment
6. Begin integration work

---

**Document Status:** Draft for Review  
**Last Updated:** 2025-11-22

