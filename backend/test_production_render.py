"""
Test production pipeline: Insert data and render edit from S3 URL
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
from app.services.ai.storytelling_agent import StorytellingAgent
from app.services.editor import EditorService
from insert_production_data import insert_from_production_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_production_render(
    video_id: str,
    story_prompt_file: str
):
    """
    Complete production test:
    1. Data should already be inserted (run insert_production_data.py first)
    2. Generate edit plan via LLM
    3. Render edit from S3 URL
    """
    logger.info("="*60)
    logger.info("PRODUCTION RENDER TEST")
    logger.info("="*60)
    logger.info(f"Video ID: {video_id}")
    
    db = SessionLocal()
    try:
        # Check media exists
        media = db.query(Media).filter(Media.video_id == video_id).first()
        if not media:
            raise ValueError(f"Media {video_id} not found. Run insert_production_data.py first.")
        
        video_url = getattr(media, 'video_url', None) or media.original_path
        logger.info(f"Video URL: {video_url}")
        logger.info(f"Duration: {media.duration_seconds:.1f}s" if media.duration_seconds else "Duration: unknown")
        
        # Load story prompt
        with open(story_prompt_file, 'r') as f:
            story_prompt_data = json.load(f)
        
        if story_prompt_data.get("type") == "tool_use":
            story_prompt = story_prompt_data.get("input", {})
        else:
            story_prompt = story_prompt_data
        
        logger.info(f"\nStory Prompt:")
        logger.info(json.dumps(story_prompt, indent=2))
        
        # Load data for LLM
        from app.services.ai.data_loader import DataLoader
        data_loader = DataLoader(db)
        
        data = data_loader.load_all_data(video_id)
        
        logger.info(f"\nLoaded data:")
        logger.info(f"  Frames: {len(data.get('frames', []))}")
        logger.info(f"  Scenes: {len(data.get('scenes', []))}")
        logger.info(f"  Transcript segments: {len(data.get('transcript_segments', []))}")
        
        # Generate edit plan
        logger.info("\n" + "="*60)
        logger.info("Generating edit plan via LLM...")
        logger.info("="*60)
        
        agent = StorytellingAgent()
        
        start_time = datetime.now()
        plan = await agent.generate_edit_plan(
            frames=data.get('frames', []),
            scenes=data.get('scenes', []),
            transcript_segments=data.get('transcript_segments', []),
            summary=data.get('summary', {}),
            story_prompt=story_prompt,
            video_duration=data.get('video_duration', 0)
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        edl = plan.get("edl", [])
        
        logger.info(f"\n✅ Edit plan generated in {elapsed:.2f}s")
        logger.info(f"EDL segments: {len(edl)}")
        
        # Calculate coverage
        keep_segments = [seg for seg in edl if seg.get("type") == "keep"]
        keep_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in keep_segments)
        coverage = (keep_duration / data.get('video_duration', 1) * 100) if data.get('video_duration', 0) > 0 else 0
        
        logger.info(f"\n📊 Edit Statistics:")
        logger.info(f"  Total 'keep' duration: {keep_duration:.1f}s")
        logger.info(f"  Coverage: {coverage:.1f}%")
        
        # Render edit from S3 URL
        logger.info("\n" + "="*60)
        logger.info("Rendering edit from S3 URL...")
        logger.info("="*60)
        
        editor = EditorService()
        
        edit_options = {
            "captions": story_prompt.get("style_preferences", {}).get("captions", True),
            "caption_style": "burn_in",
            "aspect_ratios": ["16:9", "9:16", "1:1"]  # Multiple aspect ratios
        }
        
        render_start = datetime.now()
        result = editor.render_from_edl(
            video_id=video_id,
            edl=edl,
            edit_options=edit_options
        )
        render_elapsed = (datetime.now() - render_start).total_seconds()
        
        logger.info(f"\n✅ Video rendered in {render_elapsed:.2f}s")
        logger.info(f"Output paths:")
        for aspect, path in result.get("output_paths", {}).items():
            logger.info(f"  {aspect}: {path}")
        
        logger.info(f"\n🎉 Complete! Edit rendered from S3 URL successfully!")
        
        return result
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_production_render.py <video_id> <story_prompt.json>")
        print("\nExample:")
        print("  python test_production_render.py b058ea09-d8bb-4b20-bba1-76fbdc97c929 story_prompt.json")
        sys.exit(1)
    
    video_id = sys.argv[1]
    story_prompt_file = sys.argv[2]
    
    asyncio.run(test_production_render(video_id, story_prompt_file))

