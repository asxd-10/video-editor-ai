-- Simple migration: Add level column to processing_logs table
-- Run this directly in Supabase SQL Editor

-- Check if column exists, if not add it
ALTER TABLE processing_logs 
ADD COLUMN IF NOT EXISTS level TEXT;

-- If the column was just added and is NULL, set default value
UPDATE processing_logs 
SET level = 'INFO' 
WHERE level IS NULL;

-- Make it NOT NULL with default (if needed)
ALTER TABLE processing_logs 
ALTER COLUMN level SET DEFAULT 'INFO';

-- If you want to make it NOT NULL, uncomment this (only if all rows have values):
-- ALTER TABLE processing_logs 
-- ALTER COLUMN level SET NOT NULL;

