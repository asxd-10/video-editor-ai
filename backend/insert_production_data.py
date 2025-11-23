"""
Insert production data from Friend B's sample_video_description.json
Extracts all data from the JSON file:
- Media records (video_id, video_url if available)
- Frame data (frame_level_data)
- Scene data (scene_level_data)
- Transcript data (transcription_level_data)
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media, MediaStatus
from app.models.aidit_models import Frame, SceneIndex, Transcription
from app.models.transcript import Transcript
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_video_duration_from_url(video_url: str) -> float:
    """Get video duration from S3 URL using ffprobe"""
    try:
        import ffmpeg
        # FFmpeg can probe URLs directly
        probe = ffmpeg.probe(video_url)
        duration = float(probe['format']['duration'])
        logger.info(f"Got duration from URL: {duration:.1f}s")
        return duration
    except Exception as e:
        logger.warning(f"Could not get duration from {video_url}: {e}")
        logger.warning("Will try to get duration from scenes/frames later")
        return 0.0


def get_video_duration_from_scenes(scenes: List[Dict]) -> float:
    """Get video duration from scene end times"""
    if not scenes:
        return 0.0
    max_end = max(scene.get("end", 0) for scene in scenes)
    return float(max_end)


def insert_production_media(
    db,
    video_id: str,
    video_url: Optional[str] = None,
    media_type: str = "video",
    duration: Optional[float] = None
) -> Media:
    """Insert or update media record with S3 URL"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    
    if media:
        # Update existing
        if video_url:
            media.video_url = video_url
            media.original_path = video_url  # Also set original_path
        if duration and not media.duration_seconds:
            media.duration_seconds = duration
        logger.info(f"Updated media: {video_id}")
    else:
        # Create new
        if not duration and video_url:
            duration = get_video_duration_from_url(video_url)
        
        media = Media(
            video_id=video_id,
            title=f"Video {video_id}",
            filename=video_url.split('/')[-1] if video_url else f"{video_id}.mov",
            original_filename=video_url.split('/')[-1] if video_url else f"{video_id}.mov",
            original_path=video_url or "",  # Store S3 URL as original_path
            video_url=video_url,  # Also store in video_url field
            duration_seconds=duration or 0.0,
            status=MediaStatus.READY,
            file_size=0,  # Unknown from URL
            has_audio=True  # Assume yes
        )
        db.add(media)
        logger.info(f"Created media: {video_id} ({duration:.1f}s)" if duration else f"Created media: {video_id}")
    
    db.commit()
    return media


def insert_frames_from_json(
    db,
    video_id: str,
    frame_level_data: List[Dict]
):
    """Insert frames from Friend B's JSON format"""
    inserted_count = 0
    for frame in frame_level_data:
        frame_timestamp = float(frame.get("frame_timestamp", 0))
        
        # Skip if frame already exists
        existing = db.query(Frame).filter(
            Frame.video_id == video_id,
            Frame.timestamp_seconds == frame_timestamp
        ).first()
        
        if existing:
            continue
        
        frame_record = Frame(
            video_id=video_id,
            frame_number=int(frame_timestamp),
            timestamp_seconds=frame_timestamp,
            llm_response=frame.get("description", ""),
            status="completed"
        )
        db.add(frame_record)
        inserted_count += 1
    
    db.commit()
    logger.info(f"Inserted {inserted_count} frames for {video_id} (total in JSON: {len(frame_level_data)})")


def insert_scenes_from_json(
    db,
    video_id: str,
    scene_level_data: Dict
):
    """Insert scenes from Friend B's JSON format"""
    scenes = scene_level_data.get("scenes", [])
    if not scenes:
        logger.info(f"No scenes found for {video_id}")
        return
    
    # Check if scene_index already exists
    existing = db.query(SceneIndex).filter(SceneIndex.video_id == video_id).first()
    if existing:
        logger.info(f"Scene index already exists for {video_id}, skipping")
        return
    
    scene_index = SceneIndex(
        video_id=video_id,
        video_db_id=f"videodb_{video_id}",
        index_id=f"index_{video_id}",
        extraction_type="shot_based",
        status="completed",
        scene_count=scene_level_data.get("scene_count", len(scenes)),
        scenes_data=scenes
    )
    db.add(scene_index)
    db.commit()
    logger.info(f"Inserted {len(scenes)} scenes for {video_id}")


def insert_transcript_from_json(
    db,
    video_id: str,
    transcription_level_data: Dict
):
    """Insert transcript from Friend B's JSON format (transcription_level_data)"""
    if not transcription_level_data:
        logger.info(f"No transcription data for {video_id}")
        return
    
    transcript_data = transcription_level_data.get("transcript_data", [])
    transcript_text = transcription_level_data.get("transcript_text", "")
    
    # Handle null/empty transcript
    if transcript_data is None:
        transcript_data = []
    if transcript_text is None:
        transcript_text = ""
    
    if not transcript_data and not transcript_text:
        logger.info(f"No transcript data for {video_id}, skipping")
        return
    
    # Check if transcription already exists
    existing = db.query(Transcription).filter(Transcription.video_id == video_id).first()
    if existing:
        logger.info(f"Transcription already exists for {video_id}, skipping")
    else:
        # Insert into transcriptions table (aidit format)
        transcription = Transcription(
            video_id=video_id,
            video_db_id=f"videodb_{video_id}",
            status="completed",
            transcript_data=transcript_data if transcript_data else [],
            transcript_text=transcript_text or "",
            segment_count=transcription_level_data.get("segment_count", len(transcript_data) if transcript_data else 0),
            language_code=transcription_level_data.get("language_code")
        )
        db.add(transcription)
    
    # Also insert into transcripts table (our format) for EditorService compatibility
    # Transcript model uses 'segments' field (not 'transcript_data') and doesn't have 'status' or 'transcript_text'
    if transcript_data:
        # Convert to our format: [{"start": float, "end": float, "text": str, ...}]
        transcript_segments = []
        for seg in transcript_data:
            if isinstance(seg, dict) and "text" in seg:
                # Keep all fields from original segment (start, end, text, speaker, etc.)
                segment_dict = {
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "text": seg.get("text", "")
                }
                # Add speaker if present
                if "speaker" in seg:
                    segment_dict["speaker"] = seg.get("speaker")
                transcript_segments.append(segment_dict)
        
        if transcript_segments:
            # Check if transcript already exists
            existing_transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
            if existing_transcript:
                logger.info(f"Transcript already exists for {video_id}, skipping")
            else:
                # Transcript model uses 'segments' field (not 'transcript_data')
                transcript = Transcript(
                    video_id=video_id,
                    segments=transcript_segments,  # Use 'segments' field
                    language=transcription_level_data.get("language_code", "en") or "en"
                )
                db.add(transcript)
    
    db.commit()
    segment_count = len(transcript_data) if transcript_data else 0
    logger.info(f"Inserted transcript for {video_id} ({segment_count} segments)")


def extract_video_url_from_result(result: Dict, video_id: str) -> Optional[str]:
    """
    Extract or construct video URL from result data.
    If video_url is not in the JSON, returns None (will need to be provided separately or constructed)
    """
    # Check if video_url is directly in result
    if "video_url" in result:
        return result["video_url"]
    
    # Check if there's a URL pattern we can construct
    # For now, return None - user will need to provide URLs separately or we can add pattern matching
    return None


def insert_from_json(
    json_file: str,
    video_urls: Optional[Dict[str, str]] = None
):
    """
    Insert production data from sample_video_description.json
    
    Args:
        json_file: Path to sample_video_description.json
        video_urls: Optional dict mapping video_id -> video_url
                    If not provided, will try to extract from JSON or leave as None
    """
    db = SessionLocal()
    
    try:
        # Load JSON
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        
        # Extract results array
        if "results" not in json_data:
            raise ValueError("JSON file must have 'results' array")
        
        results = json_data["results"]
        logger.info(f"Found {len(results)} videos in JSON")
        
        # Process each result
        for idx, result in enumerate(results):
            video_id = result.get("media_id")
            if not video_id:
                logger.warning(f"Skipping result {idx}: missing media_id")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing video {idx + 1}/{len(results)}: {video_id}")
            logger.info(f"{'='*60}")
            
            # Get video URL (from parameter, JSON, or None)
            video_url = None
            if video_urls and video_id in video_urls:
                video_url = video_urls[video_id]
            else:
                video_url = extract_video_url_from_result(result, video_id)
            
            if video_url:
                logger.info(f"Video URL: {video_url}")
            else:
                logger.warning(f"No video URL found for {video_id} - media record will be created without URL")
            
            # Calculate duration from scenes if available
            scene_level_data = result.get("scene_level_data", {})
            scenes = scene_level_data.get("scenes", [])
            duration = get_video_duration_from_scenes(scenes) if scenes else None
            
            # 1. Insert/update media record
            media = insert_production_media(
                db,
                video_id,
                video_url,
                "video",
                duration
            )
            
            # 2. Insert frames
            frame_level_data = result.get("frame_level_data", [])
            if frame_level_data:
                insert_frames_from_json(db, video_id, frame_level_data)
            else:
                logger.info(f"No frame data for {video_id}")
            
            # 3. Insert scenes
            if scene_level_data:
                insert_scenes_from_json(db, video_id, scene_level_data)
            else:
                logger.info(f"No scene data for {video_id}")
            
            # 4. Insert transcript
            transcription_level_data = result.get("transcription_level_data")
            if transcription_level_data:
                insert_transcript_from_json(db, video_id, transcription_level_data)
            else:
                logger.info(f"No transcription data for {video_id}")
        
        logger.info(f"\n✅ Successfully inserted {len(results)} videos from JSON")
        
    except Exception as e:
        logger.error(f"Error inserting production data: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python insert_production_data.py <sample_video_description.json> [video_urls.json]")
        print("\nExample:")
        print("  python insert_production_data.py sample_video_description.json")
        print("  python insert_production_data.py sample_video_description.json video_urls.json")
        print("\nvideo_urls.json format (optional):")
        print('  {"video_id_1": "https://...", "video_id_2": "https://..."}')
        sys.exit(1)
    
    json_file = sys.argv[1]
    video_urls = None
    
    # Optional: Load video URLs from separate file
    if len(sys.argv) > 2:
        video_urls_file = sys.argv[2]
        with open(video_urls_file, 'r') as f:
            video_urls = json.load(f)
        logger.info(f"Loaded {len(video_urls)} video URLs from {video_urls_file}")
    
    insert_from_json(json_file, video_urls)
