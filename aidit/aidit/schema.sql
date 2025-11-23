-- Database schema for aidit application
-- Run this in your Supabase SQL editor to create all required tables

-- Media table (stores video/image metadata)
CREATE TABLE IF NOT EXISTS media (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,
    video_url TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'video',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_video_id ON media(video_id);

-- Video Processing table
CREATE TABLE IF NOT EXISTS video_processing (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    granularity_seconds FLOAT NOT NULL DEFAULT 1.0,
    prompt TEXT,
    model TEXT NOT NULL DEFAULT 'google/gemini-2.0-flash-001',
    total_frames INTEGER NOT NULL DEFAULT 0,
    processed_frames INTEGER NOT NULL DEFAULT 0,
    failed_frames INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_processing_video_id ON video_processing(video_id);
CREATE INDEX IF NOT EXISTS idx_video_processing_status ON video_processing(status);

-- Image Processing table
CREATE TABLE IF NOT EXISTS image_processing (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    prompt TEXT,
    model TEXT NOT NULL DEFAULT 'google/gemini-2.0-flash-001',
    llm_response TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_processing_video_id ON image_processing(video_id);

-- Frames table
CREATE TABLE IF NOT EXISTS frames (
    id BIGSERIAL PRIMARY KEY,
    video_id BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    timestamp_seconds FLOAT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    llm_response TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, frame_number)
);

CREATE INDEX IF NOT EXISTS idx_frames_video_id ON frames(video_id);
CREATE INDEX IF NOT EXISTS idx_frames_frame_number ON frames(frame_number);

-- Scene Indexes table
CREATE TABLE IF NOT EXISTS scene_indexes (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    video_db_id TEXT NOT NULL,
    index_id TEXT NOT NULL,
    extraction_type TEXT NOT NULL DEFAULT 'shot_based',
    prompt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    scene_count INTEGER NOT NULL DEFAULT 0,
    scenes_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, index_id)
);

CREATE INDEX IF NOT EXISTS idx_scene_indexes_video_id ON scene_indexes(video_id);
CREATE INDEX IF NOT EXISTS idx_scene_indexes_index_id ON scene_indexes(index_id);
CREATE INDEX IF NOT EXISTS idx_scene_indexes_status ON scene_indexes(status);

-- Transcriptions table
CREATE TABLE IF NOT EXISTS transcriptions (
    id BIGSERIAL PRIMARY KEY,
    video_id TEXT NOT NULL UNIQUE,
    video_db_id TEXT,
    language_code TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    transcript_data JSONB,
    transcript_text TEXT,
    segment_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transcriptions_video_id ON transcriptions(video_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);

-- Processing Logs table
CREATE TABLE IF NOT EXISTS processing_logs (
    id BIGSERIAL PRIMARY KEY,
    video_id BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    frame_id BIGINT REFERENCES frames(id) ON DELETE CASCADE,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fix processing_logs table if it exists but is missing columns (for existing databases)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'processing_logs') THEN
        -- Add created_at if missing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'processing_logs' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE processing_logs 
            ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        END IF;
        
        -- Add level if missing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'processing_logs' AND column_name = 'level'
        ) THEN
            ALTER TABLE processing_logs 
            ADD COLUMN level TEXT NOT NULL DEFAULT 'INFO';
        END IF;
        
        -- Add frame_id if missing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'processing_logs' AND column_name = 'frame_id'
        ) THEN
            ALTER TABLE processing_logs 
            ADD COLUMN frame_id BIGINT REFERENCES frames(id) ON DELETE CASCADE;
        END IF;
        
        -- Ensure id is primary key if missing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'processing_logs' AND column_name = 'id'
        ) THEN
            ALTER TABLE processing_logs 
            ADD COLUMN id BIGSERIAL PRIMARY KEY;
        END IF;
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_processing_logs_video_id ON processing_logs(video_id);
        CREATE INDEX IF NOT EXISTS idx_processing_logs_frame_id ON processing_logs(frame_id);
        CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs(created_at);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_processing_logs_video_id ON processing_logs(video_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_frame_id ON processing_logs(frame_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs(created_at);

