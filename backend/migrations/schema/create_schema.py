"""
Create Unified Database Schema
Simple script to execute the SQL schema file

Usage:
    python migrations/schema/create_schema.py
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.database import engine
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def execute_sql_file():
    """Execute SQL file directly"""
    sql_file = Path(__file__).parent / "create_unified_schema.sql"
    
    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        logger.error("Make sure create_unified_schema.sql is in the same directory")
        return False
    
    logger.info("=" * 60)
    logger.info("CREATING UNIFIED DATABASE SCHEMA")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"Reading SQL file: {sql_file}")
    
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    logger.info("Executing SQL...")
    conn = engine.connect()
    
    try:
        # Execute the entire SQL file
        conn.execute(text(sql_content))
        conn.commit()
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ SCHEMA CREATED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Update your application code to use the 'media' table")
        logger.info("2. Test all endpoints")
        logger.info("3. Start using the unified schema!")
        return True
    except Exception as e:
        conn.rollback()
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ ERROR CREATING SCHEMA")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Tip: You can also run the SQL file directly in Supabase SQL Editor")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = execute_sql_file()
    sys.exit(0 if success else 1)

