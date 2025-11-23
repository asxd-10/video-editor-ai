# LLM Quality Testing - Quick Start

## Overview

This testing framework helps you evaluate and fine-tune the LLM's video editing capabilities across different scenarios and edge cases.

## Files Created

1. **`test_llm_quality.py`** - Main testing framework
2. **`test_scenarios_config.json`** - Test scenario definitions
3. **`SAMPLE_VIDEOS_FOR_TESTING.md`** - Video download guide
4. **`LLM_QUALITY_TESTING_GUIDE.md`** - Detailed testing guide
5. **`prepare_test_videos.sh`** - Helper script for downloading videos

## Quick Start (5 minutes)

### Step 1: Download Test Videos

```bash
# Option A: Use helper script
chmod +x prepare_test_videos.sh
./prepare_test_videos.sh

# Option B: Manual download
yt-dlp -f "best[height<=1080]" <YOUTUBE_URL> -o "test_video.%(ext)s"
```

### Step 2: Upload to Database

```bash
# Upload video
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@test_video.mp4"

# Get video_id from response, then:
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze
```

### Step 3: Run Tests

```bash
# Run all scenarios
python test_llm_quality.py {video_id}

# Run specific scenarios
python test_llm_quality.py {video_id} educational_short,vlog_casual

# View results
cat llm_quality_report.json | jq .
```

## Test Scenarios

### Core Scenarios
- `educational_short` - Aggressive cutting for educational content
- `vlog_casual` - Personality preservation
- `tutorial_detailed` - Step-by-step preservation
- `high_energy` - Fast-paced editing
- `emotional_story` - Emotional storytelling

### Edge Cases
- `minimal_prompt` - Minimal user input
- `empty_summary` - Missing summary
- `contradictory_preferences` - Conflicting preferences
- `very_long_video` - 30+ minute videos
- `very_short_video` - <2 minute videos

## Understanding Results

### Quality Score (0-100)
- **>80**: Good results ✅
- **50-80**: Needs improvement ⚠️
- **<50**: Poor results ❌

### Metrics Tracked
- Segment count
- Total duration
- Coverage percentage
- Average segment length
- Valid timestamps
- Large gaps

### Common Issues
- Empty EDL
- Invalid timestamps
- Too many short segments
- Coverage mismatch
- Large gaps

## Fine-Tuning Process

1. **Run tests** → Get baseline scores
2. **Review issues** → Identify patterns
3. **Adjust prompts** → Edit `prompt_builder.py`
4. **Re-test** → Compare scores
5. **Iterate** → Repeat until scores improve

## Example Workflow

```bash
# 1. Test current prompts
python test_llm_quality.py video123

# 2. Review report
cat llm_quality_report.json | jq '.results[] | {scenario: .scenario, score: .evaluation.score, issues: .evaluation.issues}'

# 3. Identify issue: "Coverage too high for 'short' edits"
# 4. Adjust prompt in prompt_builder.py
# 5. Re-test
python test_llm_quality.py video123 educational_short

# 6. Compare scores
# Before: 65/100
# After: 82/100 ✅
```

## Tips

- **Start with diverse videos**: Different lengths, content types
- **Test edge cases early**: They reveal robustness issues
- **Keep a test log**: Track what works
- **Compare manually**: Sometimes you need to watch the edits
- **Iterate quickly**: Small changes, frequent testing

## Next Steps

1. Read `LLM_QUALITY_TESTING_GUIDE.md` for detailed instructions
2. Download test videos (see `SAMPLE_VIDEOS_FOR_TESTING.md`)
3. Run initial tests
4. Review quality scores
5. Fine-tune prompts iteratively

## Support

For questions or issues:
- Check `LLM_QUALITY_TESTING_GUIDE.md` for detailed documentation
- Review test scenarios in `test_scenarios_config.json`
- Check evaluation metrics in test output

