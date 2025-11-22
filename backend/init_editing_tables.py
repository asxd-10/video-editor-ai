#!/usr/bin/env python3
"""
Initialize database tables for video editing features.
Run this script after installing dependencies to create the new tables.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.models import (
    Video, VideoAsset, UploadChunk, ProcessingLog,
    Transcript, ClipCandidate, EditJob, RetentionAnalysis
)

def main():
    print("=" * 60)
    print("Initializing Video Editing Database Tables")
    print("=" * 60)
    print()
    
    try:
        # Import all models to ensure they're registered with Base
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        print()
        print("Created tables:")
        print("  - transcripts")
        print("  - clip_candidates")
        print("  - edit_jobs")
        print("  - retention_analyses")
        print()
        print("Updated tables:")
        print("  - videos (added metadata column)")
        print()
        return 0
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

