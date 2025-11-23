"""
Test script to help test the AI edit frontend
This script:
1. Inserts production data if not already present
2. Provides a video_id to test with
3. Shows the expected story_prompt format
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_video_ids():
    """Get available video IDs from the database"""
    db = SessionLocal()
    try:
        videos = db.query(Media).filter(
            Media.video_url.isnot(None) | Media.original_path.isnot(None)
        ).limit(10).all()
        
        video_ids = []
        for video in videos:
            video_url = video.video_url or video.original_path
            video_ids.append({
                "video_id": video.video_id,
                "has_url": bool(video.video_url),
                "has_path": bool(video.original_path),
                "duration": video.duration_seconds,
                "url": video_url[:80] + "..." if video_url and len(video_url) > 80 else video_url
            })
        
        return video_ids
    finally:
        db.close()

def get_sample_story_prompt():
    """Get a sample story prompt for testing"""
    return {
        "target_audience": "young_adults",
        "tone": "energetic",
        "key_message": "Show the most exciting moments, fast-paced, hype energy",
        "desired_length": "short",
        "story_arc": {
            "hook": "Grab attention with most exciting moment in first 2 seconds",
            "build": "Rapid fire of best moments, high energy",
            "climax": "Most epic/adventurous moment",
            "resolution": "Call to action, subscribe/follow"
        },
        "style_preferences": {
            "pacing": "very_fast",
            "transitions": "dynamic",
            "emphasis": "on_highlights"
        }
    }

def get_sample_summary():
    """Get a sample summary for testing"""
    return {
        "video_summary": "A video showcasing a driving simulator setup at a university center, featuring VR technology and racing equipment.",
        "key_moments": [
            "VR headset interaction",
            "Racing simulator demonstration",
            "University center showcase"
        ],
        "content_type": "demonstration",
        "main_topics": ["technology", "gaming", "university"],
        "speaker_style": "casual"
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("AI Edit Frontend Test Helper")
    print("="*60 + "\n")
    
    # Get available videos
    print("📹 Available Videos:")
    print("-" * 60)
    videos = get_test_video_ids()
    if not videos:
        print("❌ No videos found with URLs. Please run:")
        print("   python insert_production_data.py ../sample_video_description.json")
        print("   python update_video_urls.py video_urls.json")
    else:
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['video_id']}")
            print(f"   Duration: {video['duration']:.1f}s" if video['duration'] else "   Duration: Unknown")
            print(f"   URL: {video['url']}")
            print()
    
    # Sample data
    print("\n📋 Sample Story Prompt (for testing):")
    print("-" * 60)
    print(json.dumps(get_sample_story_prompt(), indent=2))
    
    print("\n📝 Sample Summary (for testing):")
    print("-" * 60)
    print(json.dumps(get_sample_summary(), indent=2))
    
    print("\n🚀 To test:")
    print("-" * 60)
    if videos:
        test_video_id = videos[0]['video_id']
        print(f"1. Navigate to: http://localhost:5173/video/{test_video_id}/ai-edit")
        print(f"2. Use the sample story_prompt and summary above")
        print(f"3. Click 'Generate AI Edit'")
        print(f"4. Wait for plan generation")
        print(f"5. Click 'Apply Edit & Render Video'")
        print(f"6. Watch the original and edited videos side by side!")
    else:
        print("1. First insert production data and update video URLs")
        print("2. Then run this script again to get a video_id")
    
    print("\n" + "="*60)

