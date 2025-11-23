#!/usr/bin/env python3
"""
Create ai_edit_jobs table in Supabase
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, SessionLocal
from app.config import get_settings

def main():
    print("=" * 60)
    print("Creating ai_edit_jobs table")
    print("=" * 60)
    print()
    
    settings = get_settings()
    db_url = settings.get_database_url()
    
    if not db_url or db_url.startswith("sqlite"):
        print("⚠️  Database not configured or still using SQLite")
        return 1
    
    # Create table SQL (no foreign key - using media table, not videos table)
    create_table_sql = """
    -- Drop table if exists to recreate without foreign key
    DROP TABLE IF EXISTS ai_edit_jobs CASCADE;
    
    CREATE TABLE ai_edit_jobs (
        id VARCHAR(36) PRIMARY KEY,
        video_id VARCHAR(36) NOT NULL,
        summary JSONB,
        story_prompt JSONB NOT NULL,
        llm_plan JSONB,
        status VARCHAR(20) NOT NULL DEFAULT 'queued',
        error_message TEXT,
        compression_metadata JSONB,
        validation_errors JSONB,
        llm_usage JSONB,
        output_paths JSONB,
        created_at VARCHAR,
        started_at VARCHAR,
        completed_at VARCHAR
    );
    
    CREATE INDEX IF NOT EXISTS idx_ai_edit_jobs_video_id ON ai_edit_jobs(video_id);
    CREATE INDEX IF NOT EXISTS idx_ai_edit_jobs_status ON ai_edit_jobs(status);
    """
    
    db = SessionLocal()
    try:
        print("Creating ai_edit_jobs table...")
        db.execute(text(create_table_sql))
        db.commit()
        print("✅ Table created successfully!")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())

