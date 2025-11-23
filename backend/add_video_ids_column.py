#!/usr/bin/env python3
"""
Quick migration script to add video_ids column to ai_edit_jobs table.
Run this once to add the column to your database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_video_ids_column():
    """Add video_ids JSON column to ai_edit_jobs table"""
    sql = """
    ALTER TABLE ai_edit_jobs 
    ADD COLUMN IF NOT EXISTS video_ids JSONB;
    """
    
    logger.info("Adding video_ids column to ai_edit_jobs table...")
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
            logger.info("✅ Successfully added video_ids column!")
            return True
    except Exception as e:
        logger.error(f"❌ Error adding column: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Adding video_ids column to ai_edit_jobs table")
    print("=" * 60)
    print()
    
    success = add_video_ids_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the error above.")
        sys.exit(1)

