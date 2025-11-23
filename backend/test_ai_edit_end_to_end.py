"""
End-to-end test script for AI Edit feature
Tests the complete flow: data loading → LLM generation → video rendering
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_ai_edit_flow(video_id: str):
    """Test complete AI edit flow"""
    print(f"\n{'='*60}")
    print(f"Testing AI Edit Flow for video: {video_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Check data availability
    print("Step 1: Loading AI edit data...")
    response = requests.get(f"{BASE_URL}/api/videos/{video_id}/ai-edit/data")
    if response.status_code != 200:
        print(f"❌ Failed to load data: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    print(f"✅ Data loaded:")
    print(f"   - Media: {'✅' if data.get('media') else '❌'}")
    print(f"   - Transcription: {data.get('transcription', {}).get('has_data', False)} ({data.get('transcription', {}).get('segment_count', 0)} segments)")
    print(f"   - Frames: {data.get('frames', {}).get('has_data', False)} ({data.get('frames', {}).get('count', 0)} frames)")
    print(f"   - Scenes: {data.get('scenes', {}).get('has_data', False)} ({data.get('scenes', {}).get('count', 0)} scenes)")
    print(f"   - Duration: {data.get('video_duration', 0):.2f}s")
    
    if not data.get('media'):
        print("❌ No media found. Upload a video first.")
        return False
    
    # Step 2: Generate AI edit
    print("\nStep 2: Generating AI edit plan...")
    print("   Using minimal test inputs (simulating partial data from iMessage/friend's pipeline)...")
    
    # Prepare minimal story prompt (simulating partial input from iMessage app)
    # In real flow, this comes from iMessage app → preferences JSON
    story_prompt = {
        "tone": "educational",
        "key_message": "Create an engaging educational video"
        # Note: Missing fields (target_audience, story_arc, etc.) will use defaults
    }
    
    # Prepare minimal summary (simulating partial data from friend's pipeline)
    # In real flow, friend's code generates this from frames/scenes tables
    summary = {
        "video_summary": "Educational video content"
        # Note: Missing fields (key_moments, content_type, etc.) will use defaults
    }
    
    # Test with minimal data - system should handle missing fields gracefully
    payload = {
        "summary": summary,
        "story_prompt": story_prompt
    }
    
    print(f"   Summary fields: {list(summary.keys())}")
    print(f"   Story prompt fields: {list(story_prompt.keys())}")
    
    response = requests.post(
        f"{BASE_URL}/api/videos/{video_id}/ai-edit/generate",
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to generate edit: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    job_id = result.get("job_id")
    print(f"✅ Edit job created: {job_id}")
    print(f"   Status: {result.get('status')}")
    
    # Step 3: Poll for completion
    print("\nStep 3: Waiting for LLM generation to complete...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    poll_interval = 5
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/api/videos/{video_id}/ai-edit/plan/{job_id}")
        if response.status_code == 200:
            plan_data = response.json()
            status = plan_data.get("status")
            print(f"   Status: {status} (waiting {int(time.time() - start_time)}s)")
            
            if status == "completed":
                print("✅ LLM generation completed!")
                print(f"   EDL segments: {len(plan_data.get('edl', []))}")
                print(f"   Key moments: {len(plan_data.get('key_moments', []))}")
                break
            elif status == "failed":
                print(f"❌ Generation failed: {plan_data.get('error_message', 'Unknown error')}")
                return False
        else:
            print(f"   Waiting... (status check failed: {response.status_code})")
        
        time.sleep(poll_interval)
    else:
        print("❌ Timeout waiting for generation")
        return False
    
    # Step 4: Apply edit (render video)
    print("\nStep 4: Applying edit (rendering video)...")
    
    apply_payload = {
        "aspect_ratios": ["16:9"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/videos/{video_id}/ai-edit/apply/{job_id}",
        json=apply_payload
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to apply edit: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    print("✅ Edit applied successfully!")
    print(f"   Output paths: {json.dumps(result.get('output_paths', {}), indent=2)}")
    
    # Step 5: Verify output
    print("\nStep 5: Verifying output...")
    output_paths = result.get("output_paths", {})
    if output_paths:
        print("✅ Output video generated:")
        for aspect, path in output_paths.items():
            # Convert relative path to URL
            if path.startswith("../storage/"):
                url_path = path.replace("../storage/", "/storage/")
                print(f"   - {aspect}: http://127.0.0.1:8000{url_path}")
            else:
                print(f"   - {aspect}: {path}")
    else:
        print("⚠️  No output paths returned")
    
    print(f"\n{'='*60}")
    print("✅ End-to-end test completed successfully!")
    print(f"{'='*60}\n")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ai_edit_end_to_end.py <video_id>")
        print("\nExample:")
        print("  python test_ai_edit_end_to_end.py f5b0c7ad-ab9c-4e21-bfbd-a4a197c36d95")
        sys.exit(1)
    
    video_id = sys.argv[1]
    success = test_ai_edit_flow(video_id)
    sys.exit(0 if success else 1)

