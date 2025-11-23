"""
Test script for production pipeline
Simulates the actual flow:
1. Friend B's pipeline creates sample_video_description.json (frame_level_data, scene_level_data)
2. Friend A's UI creates story_prompt JSON (tool_use format)
3. Our LLM processes both to create edit plan
4. Editor applies edit to video from S3
"""
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.services.ai.storytelling_agent import StorytellingAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_production_data(video_description_file: str, story_prompt_file: str) -> Dict:
    """
    Load production data from Friend B's JSON and Friend A's story_prompt JSON
    
    Args:
        video_description_file: Path to sample_video_description.json (Friend B's output)
        story_prompt_file: Path to story_prompt.json (Friend A's output)
    
    Returns:
        Combined data structure ready for LLM processing
    """
    # Load Friend B's video description (frame_level_data, scene_level_data)
    with open(video_description_file, 'r') as f:
        video_desc = json.load(f)
    
    # Load Friend A's story prompt (tool_use format)
    with open(story_prompt_file, 'r') as f:
        story_prompt_data = json.load(f)
    
    # Extract story_prompt from tool_use format
    if story_prompt_data.get("type") == "tool_use":
        story_prompt = story_prompt_data.get("input", {})
    else:
        story_prompt = story_prompt_data
    
    # Extract frame and scene data from Friend B's format
    # Handle both direct format and nested in results array
    if "results" in video_desc and len(video_desc["results"]) > 0:
        # Friend B's API response format
        result = video_desc["results"][0]
        frame_level_data = result.get("frame_level_data", [])
        scene_level_data = result.get("scene_level_data", {})
    else:
        # Direct format
        frame_level_data = video_desc.get("frame_level_data", [])
        scene_level_data = video_desc.get("scene_level_data", {})
    
    # Normalize to our format
    frames = [
        {
            "timestamp_seconds": float(f.get("frame_timestamp", 0)),
            "llm_response": f.get("description", ""),
            "status": "completed"
        }
        for f in frame_level_data
    ]
    
    scenes = scene_level_data.get("scenes", []) if isinstance(scene_level_data, dict) else []
    
    # Extract transcript if available
    transcript_segments = video_desc.get("transcript_data", [])
    
    # Build summary from video description
    summary = {
        "video_summary": video_desc.get("video_summary", ""),
        "key_moments": [
            {
                "timestamp": scene.get("start", 0),
                "description": scene.get("description", ""),
                "importance": scene.get("metadata", {}).get("importance", "medium")
            }
            for scene in scenes
            if scene.get("metadata", {}).get("good_moment", False)
        ]
    }
    
    # Get video duration from scenes or provided duration
    video_duration = video_desc.get("duration", 0)
    if not video_duration and scenes:
        video_duration = max(scene.get("end", 0) for scene in scenes)
    
    return {
        "frames": frames,
        "scenes": scenes,
        "transcript_segments": transcript_segments,
        "summary": summary,
        "story_prompt": story_prompt,
        "video_duration": video_duration,
        "video_id": video_desc.get("video_id") or video_desc.get("media_id", "unknown")
    }


async def test_production_edit(
    video_description_file: str,
    story_prompt_file: str,
    video_url: Optional[str] = None
):
    """
    Test the complete production pipeline:
    1. Load Friend B's video description
    2. Load Friend A's story prompt
    3. Generate edit plan via LLM
    4. (Optional) Apply edit to video from S3
    """
    logger.info("="*60)
    logger.info("PRODUCTION PIPELINE TEST")
    logger.info("="*60)
    
    # Load production data
    logger.info(f"Loading video description from: {video_description_file}")
    logger.info(f"Loading story prompt from: {story_prompt_file}")
    
    data = load_production_data(video_description_file, story_prompt_file)
    
    logger.info(f"\nVideo ID: {data['video_id']}")
    logger.info(f"Duration: {data['video_duration']:.1f}s")
    logger.info(f"Frames: {len(data['frames'])}")
    logger.info(f"Scenes: {len(data['scenes'])}")
    logger.info(f"Transcript segments: {len(data['transcript_segments'])}")
    
    logger.info(f"\nStory Prompt:")
    logger.info(json.dumps(data['story_prompt'], indent=2))
    
    # Generate edit plan
    logger.info("\n" + "="*60)
    logger.info("Generating edit plan via LLM...")
    logger.info("="*60)
    
    agent = StorytellingAgent()
    
    start_time = datetime.now()
    plan = await agent.generate_edit_plan(
        frames=data['frames'],
        scenes=data['scenes'],
        transcript_segments=data['transcript_segments'],
        summary=data['summary'],
        story_prompt=data['story_prompt'],
        video_duration=data['video_duration']
    )
    elapsed = (datetime.now() - start_time).total_seconds()
    
    edl = plan.get("edl", [])
    story_analysis = plan.get("story_analysis", {})
    
    logger.info(f"\n✅ Edit plan generated in {elapsed:.2f}s")
    logger.info(f"EDL segments: {len(edl)}")
    
    # Calculate coverage
    keep_segments = [seg for seg in edl if seg.get("type") == "keep"]
    keep_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in keep_segments)
    coverage = (keep_duration / data['video_duration'] * 100) if data['video_duration'] > 0 else 0
    
    logger.info(f"\n📊 Edit Statistics:")
    logger.info(f"  Total 'keep' duration: {keep_duration:.1f}s")
    logger.info(f"  Coverage: {coverage:.1f}%")
    logger.info(f"  Desired length: {data['story_prompt'].get('desired_length', 'unknown')}")
    
    # Check if coverage is in acceptable range
    desired_length = data['story_prompt'].get('desired_length', 'short')
    if desired_length == "short":
        if 15 <= coverage <= 70:
            logger.info(f"  ✅ Coverage is acceptable (15-70% for short edits)")
        else:
            logger.warning(f"  ⚠️  Coverage is outside acceptable range (15-70% for short edits)")
    
    logger.info(f"\n📋 Generated EDL (first 10 segments):")
    for i, seg in enumerate(edl[:10], 1):
        seg_type = seg.get("type", "keep")
        duration = seg.get("end", 0) - seg.get("start", 0)
        logger.info(f"  {i}. {seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s ({seg_type}, {duration:.1f}s)")
    if len(edl) > 10:
        logger.info(f"  ... and {len(edl) - 10} more segments")
    
    logger.info(f"\n🎬 Story Analysis:")
    logger.info(json.dumps(story_analysis, indent=2))
    
    # Save results
    output_file = f"production_edit_result_{data['video_id']}.json"
    result = {
        "video_id": data['video_id'],
        "video_duration": data['video_duration'],
        "story_prompt": data['story_prompt'],
        "edl": edl,
        "story_analysis": story_analysis,
        "coverage_percentage": coverage,
        "keep_duration": keep_duration,
        "generation_time_seconds": elapsed,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"\n💾 Results saved to: {output_file}")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_production_pipeline.py <video_description.json> <story_prompt.json> [video_url]")
        print("\nExample:")
        print("  python test_production_pipeline.py ../sample_video_description.json story_prompt.json")
        sys.exit(1)
    
    video_desc_file = sys.argv[1]
    story_prompt_file = sys.argv[2]
    video_url = sys.argv[3] if len(sys.argv) > 3 else None
    
    asyncio.run(test_production_edit(video_desc_file, story_prompt_file, video_url))
