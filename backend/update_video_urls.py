"""
Update video URLs in media table from provided mapping
"""
import sys
import json
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_video_urls(video_url_mapping: List[Dict]):
    """
    Update video URLs in media table
    
    Args:
        video_url_mapping: List of dicts with 'video_id' and 'video_url'
    """
    db = SessionLocal()
    
    try:
        updated_count = 0
        not_found_count = 0
        
        for record in video_url_mapping:
            video_id = record.get("video_id")
            video_url = record.get("video_url")
            
            if not video_id or not video_url:
                logger.warning(f"Skipping record: missing video_id or video_url")
                continue
            
            # Find media record
            media = db.query(Media).filter(Media.video_id == video_id).first()
            
            if not media:
                logger.warning(f"Media not found for video_id: {video_id}")
                not_found_count += 1
                continue
            
            # Update video URL
            media.video_url = video_url
            media.original_path = video_url  # Also update original_path
            
            # Try to get duration from URL if not already set
            if not media.duration_seconds:
                try:
                    import ffmpeg
                    probe = ffmpeg.probe(video_url)
                    media.duration_seconds = float(probe['format']['duration'])
                    logger.info(f"Updated {video_id}: duration = {media.duration_seconds:.1f}s")
                except Exception as e:
                    logger.warning(f"Could not get duration for {video_id}: {e}")
            
            updated_count += 1
            logger.info(f"Updated video URL for {video_id}")
        
        db.commit()
        
        logger.info(f"\n✅ Updated {updated_count} video URLs")
        if not_found_count > 0:
            logger.warning(f"⚠️  {not_found_count} video_ids not found in database")
        
    except Exception as e:
        logger.error(f"Error updating video URLs: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_video_urls.py <video_urls.json>")
        print("\nExample:")
        print("  python update_video_urls.py video_urls.json")
        print("\nvideo_urls.json format:")
        print('  [{"video_id": "...", "video_url": "https://..."}, ...]')
        sys.exit(1)
    
    video_urls_file = sys.argv[1]
    
    with open(video_urls_file, 'r') as f:
        video_url_mapping = json.load(f)
    
    logger.info(f"Loaded {len(video_url_mapping)} video URL mappings")
    update_video_urls(video_url_mapping)

