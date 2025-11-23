"""
Comprehensive test script for EditorService component
Tests video rendering from EDL (Edit Decision List) with various edge cases
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
from app.services.editor import EditorService
from app.services.ai.edl_converter import EDLConverter
import json
import time

def test_basic_edl_rendering(video_id: str):
    """Test 1: Basic EDL rendering - simple segments"""
    print("\n" + "="*60)
    print("TEST 1: Basic EDL Rendering")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        if not media:
            print(f"❌ Video {video_id} not found")
            return False
        
        video_duration = media.duration_seconds or 0.0
        print(f"Video duration: {video_duration:.2f}s")
        
        if video_duration == 0:
            print("❌ Video duration is 0, cannot test")
            return False
        
        # Simple EDL: Keep first 10 seconds, skip middle, keep last 10 seconds
        edl = [
            {"start": 0.0, "end": min(10.0, video_duration), "type": "keep"},
            {"start": max(video_duration - 10.0, 10.0), "end": video_duration, "type": "keep"}
        ]
        
        print(f"EDL: {json.dumps(edl, indent=2)}")
        
        editor = EditorService()
        edit_options = {
            "captions": False,
            "aspect_ratios": ["16:9"]
        }
        
        start_time = time.time()
        result = editor.render_from_edl(video_id, edl, edit_options)
        elapsed = time.time() - start_time
        
        print(f"✅ Rendering completed in {elapsed:.2f}s")
        print(f"Output paths: {result['output_paths']}")
        print(f"Total edited duration: {result['total_duration']:.2f}s")
        
        # Verify output file exists
        output_path = result['output_paths'].get('16:9')
        if output_path and Path(output_path).exists():
            file_size = Path(output_path).stat().st_size
            print(f"✅ Output file exists: {output_path} ({file_size:,} bytes)")
            return True
        else:
            print(f"❌ Output file not found: {output_path}")
            return False
    finally:
        db.close()


def test_edge_case_empty_edl(video_id: str):
    """Test 2: Edge case - Empty EDL"""
    print("\n" + "="*60)
    print("TEST 2: Edge Case - Empty EDL")
    print("="*60)
    
    editor = EditorService()
    try:
        result = editor.render_from_edl(video_id, [], {})
        print("❌ Should have raised ValueError for empty EDL")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_edge_case_overlapping_segments(video_id: str):
    """Test 3: Edge case - Overlapping segments (should merge)"""
    print("\n" + "="*60)
    print("TEST 3: Edge Case - Overlapping Segments")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        # Overlapping segments
        edl = [
            {"start": 0.0, "end": 15.0, "type": "keep"},
            {"start": 10.0, "end": 25.0, "type": "keep"},  # Overlaps with first
            {"start": 20.0, "end": 30.0, "type": "keep"}   # Overlaps with second
        ]
        
        print(f"EDL with overlaps: {json.dumps(edl, indent=2)}")
        
        editor = EditorService()
        result = editor.render_from_edl(video_id, edl, {"aspect_ratios": ["16:9"]})
        
        print(f"✅ Rendered successfully")
        print(f"Output: {result['output_paths']}")
        print(f"Total duration: {result['total_duration']:.2f}s (should be ~30s, merged)")
        return True
    finally:
        db.close()


def test_edge_case_out_of_bounds(video_id: str):
    """Test 4: Edge case - Segments outside video duration"""
    print("\n" + "="*60)
    print("TEST 4: Edge Case - Out of Bounds Segments")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        # Segment that extends beyond video duration
        edl = [
            {"start": max(0, video_duration - 10), "end": video_duration + 100, "type": "keep"}
        ]
        
        print(f"EDL with out-of-bounds: {json.dumps(edl, indent=2)}")
        print(f"Video duration: {video_duration:.2f}s")
        
        editor = EditorService()
        # Should handle gracefully (clip to video duration)
        result = editor.render_from_edl(video_id, edl, {"aspect_ratios": ["16:9"]})
        
        print(f"✅ Rendered successfully (should have clipped to video duration)")
        print(f"Output: {result['output_paths']}")
        return True
    finally:
        db.close()


def test_edge_case_invalid_segment(video_id: str):
    """Test 5: Edge case - Invalid segment (start >= end)"""
    print("\n" + "="*60)
    print("TEST 5: Edge Case - Invalid Segment (start >= end)")
    print("="*60)
    
    editor = EditorService()
    edl = [
        {"start": 10.0, "end": 5.0, "type": "keep"}  # Invalid: start > end
    ]
    
    try:
        result = editor.render_from_edl(video_id, edl, {})
        print("❌ Should have raised ValueError for invalid segment")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_multiple_aspect_ratios(video_id: str):
    """Test 6: Multiple aspect ratios"""
    print("\n" + "="*60)
    print("TEST 6: Multiple Aspect Ratios")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        edl = [
            {"start": 0.0, "end": min(30.0, video_duration), "type": "keep"}
        ]
        
        editor = EditorService()
        edit_options = {
            "captions": False,
            "aspect_ratios": ["16:9", "9:16", "1:1"]
        }
        
        result = editor.render_from_edl(video_id, edl, edit_options)
        
        print(f"✅ Rendered {len(result['output_paths'])} aspect ratios:")
        for aspect, path in result['output_paths'].items():
            if Path(path).exists():
                size = Path(path).stat().st_size
                print(f"   - {aspect}: {path} ({size:,} bytes)")
            else:
                print(f"   - {aspect}: ❌ File not found")
        
        return len(result['output_paths']) == 3
    finally:
        db.close()


def test_llm_edl_format(video_id: str):
    """Test 7: LLM EDL format conversion and rendering"""
    print("\n" + "="*60)
    print("TEST 7: LLM EDL Format (with transitions and skip segments)")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        # Simulate LLM EDL format (with transitions and skip segments)
        llm_edl = [
            {"start": 0.0, "end": 10.0, "type": "keep", "reason": "Hook segment"},
            {"start": 10.0, "end": 12.0, "type": "transition", "transition_type": "fade", "transition_duration": 0.5},
            {"start": 12.0, "end": 15.0, "type": "skip", "reason": "Boring part"},
            {"start": 15.0, "end": 25.0, "type": "keep", "reason": "Main content"},
            {"start": 25.0, "end": 27.0, "type": "transition", "transition_type": "crossfade"},
            {"start": 27.0, "end": min(35.0, video_duration), "type": "keep", "reason": "Conclusion"}
        ]
        
        print(f"LLM EDL: {json.dumps(llm_edl, indent=2)}")
        
        # Convert to EditorService format
        converter = EDLConverter()
        editor_edl = converter.convert_llm_edl_to_editor_format(llm_edl)
        
        print(f"\nConverted EDL: {json.dumps(editor_edl, indent=2)}")
        print(f"Converted {len(llm_edl)} segments to {len(editor_edl)} keep segments")
        
        # Render
        editor = EditorService()
        result = editor.render_from_edl(video_id, editor_edl, {"aspect_ratios": ["16:9"]})
        
        print(f"✅ Rendered successfully")
        print(f"Output: {result['output_paths']}")
        print(f"Total duration: {result['total_duration']:.2f}s")
        
        return True
    finally:
        db.close()


def test_single_segment_full_video(video_id: str):
    """Test 8: Single segment covering full video"""
    print("\n" + "="*60)
    print("TEST 8: Single Segment (Full Video)")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        edl = [
            {"start": 0.0, "end": video_duration, "type": "keep"}
        ]
        
        editor = EditorService()
        result = editor.render_from_edl(video_id, edl, {"aspect_ratios": ["16:9"]})
        
        print(f"✅ Rendered full video")
        print(f"Output: {result['output_paths']}")
        print(f"Duration: {result['total_duration']:.2f}s (should match {video_duration:.2f}s)")
        
        return abs(result['total_duration'] - video_duration) < 0.5  # Allow small tolerance
    finally:
        db.close()


def test_very_small_segments(video_id: str):
    """Test 9: Very small segments (< 1 second)"""
    print("\n" + "="*60)
    print("TEST 9: Very Small Segments")
    print("="*60)
    
    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.video_id == video_id).first()
        video_duration = media.duration_seconds or 0.0
        
        # Multiple very small segments
        edl = [
            {"start": 0.0, "end": 0.5, "type": "keep"},
            {"start": 1.0, "end": 1.5, "type": "keep"},
            {"start": 2.0, "end": 2.5, "type": "keep"},
        ]
        
        print(f"EDL with small segments: {json.dumps(edl, indent=2)}")
        
        editor = EditorService()
        result = editor.render_from_edl(video_id, edl, {"aspect_ratios": ["16:9"]})
        
        print(f"✅ Rendered successfully")
        print(f"Output: {result['output_paths']}")
        print(f"Total duration: {result['total_duration']:.2f}s (should be ~1.5s)")
        
        return True
    finally:
        db.close()


def run_all_tests(video_id: str):
    """Run all tests"""
    print("\n" + "="*60)
    print("EDITOR SERVICE COMPREHENSIVE TEST SUITE")
    print("="*60)
    print(f"Testing with video_id: {video_id}\n")
    
    tests = [
        ("Basic EDL Rendering", test_basic_edl_rendering),
        ("Empty EDL", test_edge_case_empty_edl),
        ("Overlapping Segments", test_edge_case_overlapping_segments),
        ("Out of Bounds", test_edge_case_out_of_bounds),
        ("Invalid Segment", test_edge_case_invalid_segment),
        ("Multiple Aspect Ratios", test_multiple_aspect_ratios),
        ("LLM EDL Format", test_llm_edl_format),
        ("Single Segment (Full Video)", test_single_segment_full_video),
        ("Very Small Segments", test_very_small_segments),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func(video_id)
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_editor_service.py <video_id>")
        print("\nExample:")
        print("  python test_editor_service.py f5b0c7ad-ab9c-4e21-bfbd-a4a197c36d95")
        sys.exit(1)
    
    video_id = sys.argv[1]
    success = run_all_tests(video_id)
    sys.exit(0 if success else 1)

