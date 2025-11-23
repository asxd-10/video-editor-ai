#!/usr/bin/env python3
"""
Test AI Edit API Endpoints
Tests all endpoints with existing data from Supabase tables
"""
import sys
from pathlib import Path
import requests
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.ai.data_loader import DataLoader

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/videos"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def test_data_loader():
    """Test DataLoader service directly"""
    print_section("Testing DataLoader Service")
    
    db = SessionLocal()
    try:
        # Get first media record (source of truth for AI editing)
        from sqlalchemy import text
        result = db.execute(text("SELECT * FROM media LIMIT 1"))
        media_row = result.fetchone()
        
        if not media_row:
            print("❌ No media records found in database")
            return None
        
        media = dict(media_row._mapping)
        video_id = media.get("video_id")
        
        print(f"✅ Found media record:")
        print(f"   Media ID: {media.get('id')}")
        print(f"   Video ID: {video_id}")
        print(f"   Video URL: {media.get('video_url', 'N/A')}")
        print(f"   Media Type: {media.get('media_type', 'N/A')}")
        
        # Load data
        data_loader = DataLoader(db)
        try:
            data = data_loader.load_all_data(video_id)
            
            print(f"\n✅ Data loaded successfully:")
            print(f"   Media: {'✅' if data.get('media') else '❌'}")
            print(f"   Transcription: {'✅' if data.get('transcription') else '❌'}")
            print(f"   Frames: {len(data.get('frames', []))} frames")
            print(f"   Scenes: {len(data.get('scenes', []))} scenes")
            print(f"   Video Duration: {data.get('video_duration', 0):.2f}s")
            
            # Show transcription status
            if data.get('transcription'):
                trans = data['transcription']
                print(f"\n   Transcription Status: {trans.get('status')}")
                print(f"   Segment Count: {trans.get('segment_count', 0)}")
            
            # Show frames info
            if data.get('frames'):
                frames = data['frames']
                completed = [f for f in frames if f.get('status') == 'completed']
                print(f"\n   Frames: {len(completed)}/{len(frames)} completed")
                if completed:
                    print(f"   Sample frame: {completed[0].get('llm_response', '')[:100]}...")
            
            return video_id
            
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    finally:
        db.close()

def test_get_data_endpoint(video_id: str):
    """Test GET /api/videos/{video_id}/ai-edit/data"""
    print_section("Testing GET /ai-edit/data Endpoint")
    
    url = f"{API_BASE}/{video_id}/ai-edit/data"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_generate_endpoint(video_id: str):
    """Test POST /api/videos/{video_id}/ai-edit/generate"""
    print_section("Testing POST /ai-edit/generate Endpoint")
    
    url = f"{API_BASE}/{video_id}/ai-edit/generate"
    print(f"URL: {url}")
    
    # Sample request payload
    payload = {
        "summary": {
            "video_summary": "A test video for AI editing",
            "key_moments": [],
            "content_type": "tutorial",
            "main_topics": ["video editing"],
            "speaker_style": "casual"
        },
        "story_prompt": {
            "target_audience": "general",
            "story_arc": {
                "hook": "Grab attention in first 3 seconds",
                "build": "Build interest and context",
                "climax": "Main point/revelation",
                "resolution": "Conclusion/call-to-action"
            },
            "tone": "educational",
            "key_message": "Learn video editing basics",
            "desired_length": "medium",
            "style_preferences": {
                "pacing": "moderate",
                "transitions": "smooth",
                "emphasis": "balanced"
            }
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success!")
            print(json.dumps(data, indent=2))
            return data.get("job_id")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_get_plan_endpoint(video_id: str, job_id: str):
    """Test GET /api/videos/{video_id}/ai-edit/plan/{job_id}"""
    print_section("Testing GET /ai-edit/plan/{job_id} Endpoint")
    
    url = f"{API_BASE}/{video_id}/ai-edit/plan/{job_id}"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success!")
            print(f"Job ID: {data.get('job_id')}")
            print(f"Status: {data.get('status')}")
            
            if data.get('llm_plan'):
                plan = data['llm_plan']
                print(f"\nLLM Plan:")
                print(f"  EDL Segments: {len(plan.get('edl', []))}")
                print(f"  Key Moments: {len(plan.get('key_moments', []))}")
                print(f"  Transitions: {len(plan.get('transitions', []))}")
                
                if plan.get('story_analysis'):
                    analysis = plan['story_analysis']
                    print(f"\n  Story Analysis:")
                    print(f"    Hook: {analysis.get('hook_timestamp', 'N/A')}s")
                    print(f"    Climax: {analysis.get('climax_timestamp', 'N/A')}s")
            
            if data.get('validation_errors'):
                print(f"\n⚠️  Validation Errors: {len(data['validation_errors'])}")
                for error in data['validation_errors'][:5]:
                    print(f"    - {error}")
            
            if data.get('llm_usage'):
                usage = data['llm_usage']
                print(f"\n  LLM Usage:")
                print(f"    Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"    Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
            
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_list_jobs_endpoint(video_id: str):
    """Test GET /api/videos/{video_id}/ai-edit"""
    print_section("Testing GET /ai-edit (List Jobs) Endpoint")
    
    url = f"{API_BASE}/{video_id}/ai-edit"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success!")
            print(f"Total Jobs: {len(data.get('jobs', []))}")
            for job in data.get('jobs', []):
                print(f"\n  Job {job['id'][:8]}...")
                print(f"    Status: {job['status']}")
                print(f"    Created: {job.get('created_at', 'N/A')}")
                print(f"    Has Plan: {job.get('has_plan', False)}")
                print(f"    Has Output: {job.get('has_output', False)}")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def wait_for_job_completion(video_id: str, job_id: str, max_wait: int = 300):
    """Wait for job to complete, polling every 5 seconds"""
    print_section("Waiting for Job Completion")
    
    import time
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        url = f"{API_BASE}/{video_id}/ai-edit/plan/{job_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                print(f"Status: {status} (elapsed: {int(time.time() - start_time)}s)")
                
                if status == 'completed':
                    print("\n✅ Job completed!")
                    return True
                elif status == 'failed':
                    print(f"\n❌ Job failed: {data.get('error_message', 'Unknown error')}")
                    return False
                
                time.sleep(5)
            else:
                print(f"⚠️  Error checking status: {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(5)
    
    print(f"\n⏱️  Timeout after {max_wait}s")
    return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("  AI Edit API Endpoint Testing")
    print("=" * 60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}\n")
    
    # Step 1: Test DataLoader
    video_id = test_data_loader()
    if not video_id:
        print("\n❌ Cannot proceed without video data")
        return
    
    # Step 2: Test GET /ai-edit/data
    if not test_get_data_endpoint(video_id):
        print("\n⚠️  Data endpoint failed, but continuing...")
    
    # Step 3: Test POST /ai-edit/generate
    job_id = test_generate_endpoint(video_id)
    if not job_id:
        print("\n❌ Generate endpoint failed")
        return
    
    # Step 4: Wait for job completion
    print(f"\n⏳ Waiting for job {job_id[:8]}... to complete...")
    if wait_for_job_completion(video_id, job_id):
        # Step 5: Test GET /ai-edit/plan/{job_id}
        test_get_plan_endpoint(video_id, job_id)
    
    # Step 6: Test GET /ai-edit (list jobs)
    test_list_jobs_endpoint(video_id)
    
    print("\n" + "=" * 60)
    print("  Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()

