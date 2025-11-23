"""
Script to insert test dataset into database for LLM quality testing
Simulates friend's pipeline output format
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media, MediaStatus
from app.models.aidit_models import Frame, SceneIndex, Transcription
from sqlalchemy import text

def insert_test_video(db, video_data: dict):
    """Insert a test video with all its data"""
    video_id = video_data["video_id"]
    
    # 1. Insert media record
    media = Media(
        video_id=video_id,
        title=video_data.get("description", ""),
        filename=f"{video_id}.mp4",
        original_filename=f"{video_id}.mp4",
        original_path=f"../storage/uploads/{video_id}/video.mp4",
        duration_seconds=video_data.get("duration", 0),
        status=MediaStatus.READY,
        file_size=1000000,  # Dummy size
        has_audio=True
    )
    db.add(media)
    db.commit()
    
    # 2. Insert frames (friend's format: frame_timestamp, description)
    frame_data = video_data.get("frame_level_data", [])
    for frame in frame_data:
        frame_record = Frame(
            video_id=video_id,
            frame_number=int(frame.get("frame_timestamp", 0)),
            timestamp_seconds=float(frame.get("frame_timestamp", 0)),
            llm_response=frame.get("description", ""),
            status="completed"
        )
        db.add(frame_record)
    
    # 3. Insert scenes (friend's format: scenes array in scene_level_data)
    scene_data = video_data.get("scene_level_data", {})
    if scene_data.get("scenes"):
        scene_index = SceneIndex(
            video_id=video_id,
            video_db_id=f"videodb_{video_id}",
            index_id=f"index_{video_id}",
            extraction_type="shot_based",
            status="completed",
            scene_count=scene_data.get("scene_count", 0),
            scenes_data=scene_data.get("scenes", [])
        )
        db.add(scene_index)
    
    # 4. Insert transcription
    transcript_data = video_data.get("transcript_data", [])
    if transcript_data:
        transcription = Transcription(
            video_id=video_id,
            video_db_id=f"videodb_{video_id}",
            status="completed",
            transcript_data=transcript_data,
            transcript_text=" ".join(seg.get("text", "") for seg in transcript_data),
            segment_count=len(transcript_data),
            language_code="en"
        )
        db.add(transcription)
    
    db.commit()
    print(f"✅ Inserted test video: {video_id} ({video_data.get('duration', 0):.1f}s)")
    return video_id


def main():
    if len(sys.argv) < 2:
        print("Usage: python insert_test_data.py <test_dataset_file.json>")
        print("Example: python insert_test_data.py test_dataset_short_form.json")
        sys.exit(1)
    
    test_file = sys.argv[1]
    
    # Load test dataset
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    db = SessionLocal()
    try:
        video_ids = []
        
        # Insert all test videos
        for video_data in test_data.get("test_videos", []):
            video_id = insert_test_video(db, video_data)
            video_ids.append(video_id)
        
        # Insert edge case videos
        for video_data in test_data.get("edge_case_videos", []):
            video_id = insert_test_video(db, video_data)
            video_ids.append(video_id)
        
        print(f"\n✅ Inserted {len(video_ids)} test videos")
        print(f"Video IDs: {', '.join(video_ids)}")
        print("\nNow you can run:")
        print(f"  python test_short_form_quality.py {test_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

