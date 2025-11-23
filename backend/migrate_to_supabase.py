#!/usr/bin/env python3
"""
Migration script to set up Supabase database.
This will create all tables in your Supabase PostgreSQL database.
"""
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.config import get_settings
from app.models import (
    Video, VideoAsset, UploadChunk, ProcessingLog,
    Transcript, ClipCandidate, EditJob, RetentionAnalysis
)

def main():
    print("=" * 60)
    print("Supabase Database Migration")
    print("=" * 60)
    print()
    
    # Use Settings class which loads from .env file
    settings = get_settings()
    db_url = settings.get_database_url()
    
    if not db_url or db_url.startswith("sqlite"):
        print("⚠️  Database not configured or still using SQLite")
        print()
        print("   Set individual components in backend/.env file (Session Pooler):")
        print("   user=postgres.ujertelpchurerutnjpp")
        print("   password=YOUR_PASSWORD")
        print("   host=aws-0-us-west-2.pooler.supabase.com")
        print("   port=5432")
        print("   dbname=postgres")
        print()
        print("   Or use full DATABASE_URL:")
        print("   DATABASE_URL=postgresql+psycopg2://postgres.ujertelpchurerutnjpp:password@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require")
        return 1
    
    if not db_url.startswith("postgresql"):
        print("⚠️  Connection string doesn't look like PostgreSQL")
        print(f"   Current value: {db_url[:50]}...")
        return 1
    
    # Show database host (hide password)
    if '@' in db_url:
        db_host = db_url.split('@')[1].split('/')[0]
        print(f"✅ Using database: {db_host}")
    else:
        print(f"✅ Using database: (connection configured)")
    print()
    
    try:
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully in Supabase!")
        print()
        print("Created tables:")
        print("  - videos")
        print("  - video_assets")
        print("  - upload_chunks")
        print("  - processing_logs")
        print("  - transcripts")
        print("  - clip_candidates")
        print("  - edit_jobs")
        print("  - retention_analyses")
        print()
        return 0
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

