# Production Pipeline Testing

## Overview

This tests the actual production flow:
1. **Friend B's Pipeline**: Processes video → creates `sample_video_description.json` (frame_level_data, scene_level_data)
2. **Friend A's UI**: User preferences → creates `story_prompt.json` (tool_use format)
3. **Our LLM**: Processes both → generates edit plan (EDL)
4. **Editor**: Applies edit to video from S3 bucket

## Data Flow

```
iPhone iMessage (Friend A)
  ↓
Database X (conversation + attachments)
  ↓
Friend B's Pipeline (aidit)
  ↓
sample_video_description.json {
  frame_level_data: [...],
  scene_level_data: {...},
  transcript_data: [...],
  duration: 38.5,
  video_id: "..."
}
  ↓
Friend A's UI (user preferences)
  ↓
story_prompt.json {
  type: 'tool_use',
  name: 'create_storyboard',
  input: {
    target_audience: 'general',
    story_arc: {...},
    tone: 'entertaining',
    desired_length: 'short',
    ...
  }
}
  ↓
Our LLM Pipeline
  ↓
Edit Plan (EDL) → Editor → Final Video
```

## Coverage Range Update

**Changed from 15-30% to 15-70%** for "short" edits because:
- Original videos may already be short (e.g., 20s)
- For short originals, keeping 50-70% is acceptable
- For long originals, aim for 15-30% to create engaging short-form content

## Testing

### Quick Test
```bash
python test_production_pipeline.py sample_video_description.json story_prompt.json
```

### Expected Input Format

**sample_video_description.json** (Friend B's output):
```json
{
  "video_id": "abc123",
  "duration": 38.5,
  "frame_level_data": [
    {
      "frame_timestamp": 0,
      "description": "Frame description..."
    }
  ],
  "scene_level_data": {
    "scene_count": 5,
    "scenes": [
      {
        "start": 0.0,
        "end": 8.0,
        "description": "Scene description...",
        "metadata": {
          "importance": "high",
          "good_moment": true
        }
      }
    ]
  },
  "transcript_data": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Transcript text..."
    }
  ]
}
```

**story_prompt.json** (Friend A's output):
```json
{
  "type": "tool_use",
  "id": "toolu_01VYjk2cnimhN5zKsqmK4Cth",
  "name": "create_storyboard",
  "input": {
    "target_audience": "general",
    "story_arc": {
      "hook": "Quick exterior shot...",
      "build": "Series of shots...",
      "climax": "Friend trying to navigate...",
      "resolution": "Final shots..."
    },
    "tone": "entertaining",
    "key_message": "Fun tech adventures...",
    "desired_length": "short",
    "style_preferences": {
      "pacing": "fast",
      "transitions": "dynamic",
      "emphasis": "balanced"
    }
  }
}
```

## Output

The script generates:
- `production_edit_result_{video_id}.json` with:
  - EDL (Edit Decision List)
  - Story analysis
  - Coverage percentage
  - Generation time

## Next Steps

1. **Get production data**: Obtain actual `sample_video_description.json` and `story_prompt.json` from friends
2. **Test with real data**: Run `test_production_pipeline.py` with production files
3. **Optimize prompts**: Based on results, fine-tune LLM prompts
4. **Integrate with S3**: Add video download from S3 bucket URL
5. **Apply edits**: Use EditorService to render final video

## Notes

- Videos are stored in S3 bucket with URLs in `media` table
- Focus is on LLM pipeline optimization (not upload/processing)
- Coverage range is now 15-70% for flexibility with short originals

