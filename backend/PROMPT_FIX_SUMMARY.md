# Prompt Fix Summary - Coverage Issue

## Problem Identified
The LLM is keeping **87-100% coverage** for "short" edits when it should be **15-30% coverage**.

### Test Results Showing Issue:
- `test_short_001` (high_energy_hype_reel): **100% coverage** ❌ (should be 15-30%)
- `test_short_001` (quick_tips_tutorial): **100% coverage** ❌ (should be 15-30%)
- `test_short_002` (quick_review_short): **87.1% coverage** ❌ (should be 15-30%)
- `test_short_004` (quick_tutorial_fast): **40.0% coverage** ⚠️ (should be 15-30%)
- `test_short_005` (high_energy_workout): **89.1% coverage** ❌ (should be 15-30%)

## Root Cause
The prompt was not explicit enough about:
1. **How to calculate coverage** (only count "keep" segments)
2. **What coverage means** (15-30% = aggressive cutting, not "fast pacing")
3. **Verification step** (calculate before finalizing)

## Fixes Applied

### 1. System Prompt Enhancement
- Added explicit calculation examples
- Emphasized that 87-100% coverage = FAILURE for 'short' edits
- Made it clear this is MANDATORY, not optional

### 2. Task Prompt Enhancement
- Added detailed coverage calculation with video-specific numbers
- Added EDL example showing correct vs wrong approach
- Added verification step (calculate coverage before finalizing)

### 3. EDL Creation Instructions
- Explicitly state: "Count only 'keep' segments, ignore 'skip' segments"
- Added example showing 8.5s keep from 38s video (22% coverage) ✅
- Added wrong example showing 38.5s keep (100% coverage) ❌

## Expected Behavior After Fix

For a 38.5s video with `desired_length='short'`:
- **Target**: 5.8s to 11.6s of "keep" segments (15-30% of 38.5s)
- **EDL should have**: Multiple "keep" segments (1-3s each) + many "skip" segments
- **Coverage**: 15-30% (not 87-100%)

## Next Steps

1. **Re-run tests**: `python test_short_form_quality.py test_dataset_short_form.json`
2. **Check coverage**: Should see 15-30% for all "short" edits
3. **Verify EDL**: Should have many "skip" segments, few "keep" segments
4. **If still failing**: May need to add post-processing validation that rejects EDLs with >30% coverage for 'short' edits

## Verification Logic

The evaluation already correctly calculates coverage:
```python
total_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in edl)
coverage_percentage = (total_duration / video_duration * 100)
```

**Issue**: This counts ALL segments (keep + skip). We need to count ONLY "keep" segments.

Wait - let me check the evaluation code...

