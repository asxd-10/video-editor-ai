-- Migration: Add level column to processing_logs table
-- Run this in your Supabase SQL Editor if you get "Could not find the 'level' column" error

ALTER TABLE processing_logs 
ADD COLUMN IF NOT EXISTS level TEXT NOT NULL DEFAULT 'INFO';

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'processing_logs'
ORDER BY ordinal_position;

