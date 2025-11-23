"""
Helper script to wait for video processing to complete before testing
"""
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
from app.models.aidit_models import Transcription, SceneIndex, Frame

def check_processing_status(video_id: str) -> dict:
    """Check if video has transcription, scenes, and frames"""
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        if not media:
            return {"error": "Video not found"}
        
        # Check transcription
        transcription = db.query(Transcription).filter(
            Transcription.video_id == video_id,
            Transcription.status == 'completed'
        ).first()
        
        # Check scenes
        scenes = db.query(SceneIndex).filter(
            SceneIndex.video_id == video_id,
            SceneIndex.status == 'completed'
        ).first()
        
        # Check frames
        frame_count = db.query(Frame).filter(
            Frame.video_id == video_id
        ).count()
        
        return {
            "video_id": video_id,
            "duration": media.duration_seconds,
            "status": media.status,
            "has_transcription": transcription is not None,
            "transcription_segments": len(transcription.transcript_data) if transcription and transcription.transcript_data else 0,
            "has_scenes": scenes is not None,
            "scene_count": scenes.scene_count if scenes else 0,
            "frame_count": frame_count,
            "ready_for_testing": (
                transcription is not None and 
                (scenes is not None or frame_count > 0)
            )
        }
    finally:
        db.close()

def wait_for_processing(video_id: str, timeout: int = 300, check_interval: int = 5):
    """Wait for video processing to complete"""
    print(f"Waiting for processing to complete for video: {video_id}")
    print(f"Timeout: {timeout}s, Check interval: {check_interval}s")
    print()
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = check_processing_status(video_id)
        
        if status.get("error"):
            print(f"❌ Error: {status['error']}")
            return False
        
        print(f"Status check:")
        print(f"  Duration: {status.get('duration', 0):.2f}s")
        print(f"  Media status: {status.get('status')}")
        print(f"  Transcription: {'✅' if status.get('has_transcription') else '❌'} ({status.get('transcription_segments', 0)} segments)")
        print(f"  Scenes: {'✅' if status.get('has_scenes') else '❌'} ({status.get('scene_count', 0)} scenes)")
        print(f"  Frames: {status.get('frame_count', 0)}")
        print()
        
        if status.get("ready_for_testing"):
            print("✅ Video is ready for testing!")
            return True
        
        print(f"⏳ Waiting {check_interval}s before next check...")
        time.sleep(check_interval)
    
    print(f"❌ Timeout after {timeout}s. Processing may still be in progress.")
    return False

def trigger_processing(video_id: str):
    """Trigger transcription and analysis if not already started"""
    base_url = "http://localhost:8000"
    
    # Check if transcription exists
    try:
        response = requests.get(f"{base_url}/api/videos/{video_id}/transcript/status")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "complete":
                print("✅ Transcription already exists")
            else:
                print("📝 Starting transcription...")
                response = requests.post(f"{base_url}/api/videos/{video_id}/transcribe")
                if response.status_code == 200:
                    print("✅ Transcription queued")
                elif response.status_code == 404:
                    print(f"❌ Video not found. Make sure video_id is correct: {video_id}")
                else:
                    print(f"❌ Failed to start transcription: {response.status_code} - {response.text}")
        else:
            print(f"⚠️  Could not check transcription status: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Could not check transcription status: {e}")
    
    # Trigger analysis (if endpoint exists)
    try:
        print("🔍 Starting analysis...")
        response = requests.post(f"{base_url}/api/videos/{video_id}/analyze")
        if response.status_code == 200:
            print("✅ Analysis queued")
        elif response.status_code == 404:
            print(f"⚠️  Video not found for analysis endpoint")
        else:
            print(f"⚠️  Analysis endpoint returned: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️  Could not trigger analysis: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wait_for_processing.py <video_id> [--trigger]")
        print("\nOptions:")
        print("  --trigger  Trigger transcription/analysis if not started")
        sys.exit(1)
    
    video_id = sys.argv[1]
    should_trigger = "--trigger" in sys.argv
    
    if should_trigger:
        trigger_processing(video_id)
        print()
        time.sleep(2)  # Give tasks a moment to queue
    
    success = wait_for_processing(video_id)
    sys.exit(0 if success else 1)

