# EditorService Test Requirements & Edge Cases

## Functional Requirements

### Core Functionality
1. ✅ **Render video from EDL** - Given a list of segments `[{start, end, type: "keep"}]`, extract and concatenate segments
2. ✅ **Support multiple aspect ratios** - Render same EDL in different aspect ratios (16:9, 9:16, 1:1)
3. ✅ **Handle captions** - Optionally add captions/subtitles to rendered video
4. ✅ **Audio preservation** - Maintain audio track when available, normalize if needed
5. ✅ **Output file generation** - Create valid MP4 files in processed directory

### EDL Format
- **Input Format**: `[{"start": float, "end": float, "type": "keep"}]`
- **Validation**: 
  - Start < End
  - Start >= 0
  - End <= video_duration (with warnings for out-of-bounds)
  - Duration >= 0.1 seconds (skip segments that are too small)

### Rendering Process
1. Extract each segment from source video using FFmpeg
2. Apply aspect ratio conversion if needed
3. Concatenate segments using FFmpeg concat demuxer
4. Add captions if enabled
5. Normalize audio if available
6. Output final MP4 with faststart flag for streaming

## Edge Cases to Test

### 1. ✅ Empty EDL
- **Expected**: Raise `ValueError` with clear message
- **Test**: `test_edge_case_empty_edl()`

### 2. ✅ Invalid Segments
- **Start >= End**: Raise `ValueError`
- **Test**: `test_edge_case_invalid_segment()`

### 3. ✅ Overlapping Segments
- **Behavior**: Should merge overlapping segments automatically
- **Test**: `test_edge_case_overlapping_segments()`

### 4. ✅ Out of Bounds Segments
- **Behavior**: Log warning, clip to video duration
- **Test**: `test_edge_case_out_of_bounds()`

### 5. ✅ Very Small Segments (< 0.1s)
- **Behavior**: Skip segments that are too small (FFmpeg may fail on very short segments)
- **Test**: `test_very_small_segments()`

### 6. ✅ Single Segment (Full Video)
- **Behavior**: Should render entire video without issues
- **Test**: `test_single_segment_full_video()`

### 7. ✅ Multiple Aspect Ratios
- **Behavior**: Render same EDL in different aspect ratios
- **Test**: `test_multiple_aspect_ratios()`

### 8. ✅ LLM EDL Format
- **Behavior**: Convert LLM format (with transitions/skip) to EditorService format
- **Test**: `test_llm_edl_format()`

### 9. ✅ Basic Rendering
- **Behavior**: Simple 2-segment EDL should render correctly
- **Test**: `test_basic_edl_rendering()`

## Additional Edge Cases (Not Yet Tested)

### 10. ⚠️ Segments at Video Boundaries
- **Start = 0.0, End = video_duration**: Should work
- **Start very close to 0**: Should work
- **End very close to video_duration**: Should work

### 11. ⚠️ Many Small Segments
- **Behavior**: 50+ small segments should render without performance issues
- **Concern**: FFmpeg concat might be slow with many segments

### 12. ⚠️ Segments with Gaps
- **Behavior**: Gaps between segments should create jump cuts (no transitions yet)
- **Example**: `[0-10s, 20-30s]` should render as jump cut

### 13. ⚠️ Video Without Audio
- **Behavior**: Should render video-only without errors
- **Current**: Handled with `has_audio` flag

### 14. ⚠️ Video with Corrupted Segments
- **Behavior**: Should handle gracefully (skip or error)
- **Note**: FFmpeg will fail if segment extraction fails

### 15. ⚠️ Concurrent Rendering
- **Behavior**: Multiple renders for same video should not conflict
- **Note**: Temp directories use unique names per render

## Performance Considerations

1. **Segment Extraction**: Each segment requires separate FFmpeg call
2. **Concat Operation**: Single FFmpeg call to concatenate all segments
3. **Aspect Ratio Conversion**: Applied per segment (could be optimized)
4. **Temp File Cleanup**: Should clean up temp segment files after rendering

## Error Handling

1. **Video Not Found**: Raise `ValueError` with clear message
2. **FFmpeg Errors**: Log error, raise exception with FFmpeg stderr
3. **Invalid EDL**: Validate before rendering, raise `ValueError`
4. **File System Errors**: Handle permission issues, disk space, etc.

## Output Validation

After rendering, verify:
1. ✅ Output file exists
2. ✅ File size > 0
3. ✅ File is valid MP4 (can be probed with FFmpeg)
4. ✅ Duration matches expected (sum of segment durations)
5. ✅ Video has correct aspect ratio
6. ✅ Audio track exists (if source had audio)

## Test Script Usage

```bash
cd backend
python test_editor_service.py <video_id>
```

The test script will:
1. Run all 9 test cases
2. Report pass/fail for each
3. Show output file paths and sizes
4. Validate output files exist

## Integration with AI Edit Flow

The `render_from_edl()` method is used by:
- `apply_ai_edit()` endpoint in `ai_edit.py`
- Converts LLM EDL → EditorService EDL → Renders video
- Stores result in `EditJob` table

## Future Enhancements

1. **Transitions**: Currently skipped, could add fade/crossfade between segments
2. **Dynamic Zoom**: Detect faces/objects and apply zoom
3. **Pace Optimization**: Speed up/slow down segments based on content
4. **Batch Rendering**: Render multiple aspect ratios in parallel
5. **Progress Tracking**: Report rendering progress for long videos

