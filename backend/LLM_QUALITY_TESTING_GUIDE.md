# LLM Quality Testing Guide

## Overview

This guide helps you test and fine-tune the LLM's video editing capabilities. The testing framework evaluates:
- EDL quality (segment selection, timestamps, coverage)
- Story alignment (does it match user preferences?)
- Edge case handling (missing data, contradictory preferences, etc.)
- Prompt effectiveness (which prompts produce better results?)

## Quick Start

### 1. Prepare Test Videos

```bash
# Download sample videos (see SAMPLE_VIDEOS_FOR_TESTING.md)
yt-dlp -f "best[height<=1080]" <YOUTUBE_URL> -o "test_video.%(ext)s"

# Upload to database
curl -X POST http://localhost:8000/api/videos/upload -F "file=@test_video.mp4"

# Get video_id from response, then trigger processing
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze
```

### 2. Run Tests

```bash
# Run all scenarios
python test_llm_quality.py {video_id}

# Run specific scenarios
python test_llm_quality.py {video_id} educational_short,vlog_casual

# View results
cat llm_quality_report.json
```

## Test Scenarios

### Core Scenarios

1. **educational_short**: Aggressive cutting for educational content
2. **vlog_casual**: Personality preservation for vlogs
3. **tutorial_detailed**: Step-by-step preservation
4. **high_energy**: Fast-paced, dynamic editing
5. **emotional_story**: Emotional storytelling with arc

### Edge Cases

1. **minimal_prompt**: Minimal user input
2. **empty_summary**: Missing summary data
3. **contradictory_preferences**: Conflicting preferences
4. **very_long_video**: 30+ minute videos
5. **very_short_video**: <2 minute videos

## Evaluation Metrics

### Quality Score (0-100)

Calculated based on:
- **Validation**: -20 if timestamps invalid
- **Issues**: -5 per issue found
- **Coverage**: +10 if 20-80% (reasonable)
- **Segment Count**: +10 if 3-20 segments (reasonable)
- **Empty EDL**: Score = 0

### Metrics Tracked

1. **Segment Count**: Number of segments in EDL
2. **Total Duration**: Sum of all segment durations
3. **Coverage Percentage**: (Total Duration / Video Duration) × 100
4. **Average Segment Length**: Total Duration / Segment Count
5. **Has Transitions**: Whether transitions are included
6. **Valid Timestamps**: All segments within video duration
7. **Large Gaps**: Gaps >5 seconds between segments

### Common Issues Detected

- Empty EDL
- Invalid timestamps (out of bounds)
- Too many very short segments (<1s)
- Large gaps between segments (>5s)
- Coverage mismatch (e.g., "short" but >30% of original)

## Interpreting Results

### Good Results (Score >80)

- ✅ Valid timestamps
- ✅ Reasonable coverage (matches desired_length)
- ✅ Appropriate segment count
- ✅ No large gaps
- ✅ Story alignment matches preferences

### Needs Improvement (Score 50-80)

- ⚠️ Some issues found
- ⚠️ Coverage might not match desired_length
- ⚠️ Some validation warnings

### Poor Results (Score <50)

- ❌ Multiple issues
- ❌ Invalid timestamps
- ❌ Empty or very short EDL
- ❌ Doesn't match user preferences

## Fine-Tuning Prompts

### Based on Test Results

1. **If coverage is too high/low**:
   - Adjust prompt to emphasize desired_length
   - Add examples of good coverage percentages

2. **If segments are too short**:
   - Add minimum segment length requirement
   - Emphasize preserving complete thoughts

3. **If story arc is not followed**:
   - Strengthen story_arc instructions
   - Add examples of good story structure

4. **If key moments are missed**:
   - Emphasize importance of key_moments
   - Add validation for key moment coverage

### Prompt Iteration Process

1. Run tests on sample videos
2. Review quality scores and issues
3. Identify patterns (e.g., "always cuts too aggressively")
4. Adjust prompt in `prompt_builder.py`
5. Re-run tests
6. Compare scores before/after
7. Iterate until scores improve

## Test Report Structure

```json
{
  "test_run": "2025-02-05T...",
  "total_scenarios": 10,
  "successful": 8,
  "failed": 1,
  "skipped": 1,
  "average_score": 75.5,
  "results": [
    {
      "scenario": "educational_short",
      "status": "success",
      "evaluation": {
        "score": 85.0,
        "metrics": {...},
        "issues": []
      },
      "edl": [...],
      "story_analysis": {...}
    }
  ]
}
```

## Best Practices

1. **Test with Real Videos**: Use actual content, not synthetic data
2. **Test Multiple Scenarios**: Don't just test one use case
3. **Track Over Time**: Run tests after each prompt change
4. **Compare Scores**: Before/after comparisons are key
5. **Review EDLs Manually**: Sometimes scores don't tell the full story
6. **Test Edge Cases**: They reveal robustness issues

## Common Issues & Solutions

### Issue: EDL is empty
**Cause**: LLM didn't generate valid segments
**Solution**: Check prompt, add validation examples

### Issue: Coverage too high/low
**Cause**: LLM not following desired_length
**Solution**: Emphasize desired_length in prompt, add examples

### Issue: Invalid timestamps
**Cause**: LLM hallucinating timestamps
**Solution**: Strengthen timestamp validation instructions

### Issue: Too many short segments
**Cause**: Over-aggressive cutting
**Solution**: Add minimum segment length requirement

### Issue: Large gaps
**Cause**: Missing important content
**Solution**: Emphasize coverage and completeness

## Next Steps

1. Run initial tests on your videos
2. Review quality scores
3. Identify patterns in issues
4. Adjust prompts iteratively
5. Re-test and compare
6. Document successful prompt patterns

## Tips for Effective Testing

- **Start with diverse videos**: Different lengths, content types, styles
- **Test edge cases early**: They reveal robustness issues
- **Keep a test log**: Track what works and what doesn't
- **Compare manually**: Sometimes you need to watch the edits
- **Iterate quickly**: Small prompt changes, frequent testing
- **Document findings**: What prompts work best for which scenarios?

