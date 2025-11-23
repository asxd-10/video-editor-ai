# Unified Schema

This directory contains the unified database schema that combines both codebases.

## Files

- **`create_unified_schema.sql`** - Complete SQL schema definition
- **`create_schema.py`** - Python script to create the schema

## Quick Start

### Option 1: Run SQL in Supabase (Recommended)

1. Open your Supabase project dashboard
2. Go to **SQL Editor**
3. Copy and paste the contents of `create_unified_schema.sql`
4. Click **Run**

### Option 2: Use Python Script

```bash
cd backend
python migrations/schema/create_schema.py
```

## Schema Overview

The unified schema includes:

### Core Tables
- `media` - Unified media table (replaces both `videos` and aidit `media`)
- `video_processing` - Frame processing status
- `frames` - Frame-level data with LLM responses
- `scene_indexes` - Scene extraction results
- `transcriptions` - Unified transcription data

### Asset Tables
- `video_assets` - Proxy videos, thumbnails
- `upload_chunks` - Chunked upload tracking

### Processing Tables
- `processing_logs` - Processing audit trail
- `image_processing` - Single image processing

### Editing Tables
- `clip_candidates` - AI-generated clip suggestions
- `edit_jobs` - Video editing jobs
- `retention_analysis` - Retention curve analysis
- `ai_edit_jobs` - AI storytelling edit jobs

## Key Features

✅ **Unified `media` table** - Single source of truth  
✅ **Supports both file and URL uploads**  
✅ **All foreign keys reference `media.video_id`**  
✅ **JSONB for complex data**  
✅ **Proper indexes for performance**

