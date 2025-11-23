# LLM Input Format Verification

## What the LLM Actually Receives

### Current Inputs (Verified)

1. **Frames** (from `frames` table or friend's pipeline):
   - Format: `{timestamp_seconds, llm_response}` OR `{frame_timestamp, description}`
   - Source: Database `frames` table
   - Processing: Normalized to `{timestamp_seconds, llm_response}` format
   - Compression: Limited to 50 frames max

2. **Scenes** (from `scene_indexes` table):
   - Format: `{start, end, description, ...}`
   - Source: Database `scene_indexes.scenes_data` (JSONB)
   - Processing: Extracted from `scenes_data` array
   - Compression: Limited to 20 scenes max

3. **Transcript** (from `transcriptions` table):
   - Format: `{start, end, text, ...}`
   - Source: Database `transcriptions.transcript_data` (JSONB)
   - Processing: Extracted from `transcript_data` array
   - Compression: Limited to 100 segments max

4. **Summary** (from user input or database):
   - Format: `{video_summary, key_moments, content_type, main_topics, speaker_style}`
   - Source: User input (from iMessage app) OR database
   - Processing: Handles missing/partial data gracefully

5. **Story Prompt** (from user input):
   - Format: `{target_audience, tone, key_message, desired_length, story_arc, style_preferences}`
   - Source: User input (from iMessage app)
   - Processing: Handles missing/partial data gracefully

## Friend's Pipeline Format

### Input Format (from iMessage/StoryStudio)

```json
{
  "frame_level_data": [
    {
      "frame_timestamp": 0,
      "description": "Frame description from LLM..."
    }
  ],
  "scene_level_data": {
    "scene_count": 1,
    "scenes": [
      {
        "start": 0.0,
        "end": 24.097,
        "description": "Scene description...",
        "metadata": {},
        "scene_metadata": {}
      }
    ]
  }
}
```

### Our Database Format

```json
{
  "frames": [
    {
      "timestamp_seconds": 0.0,
      "llm_response": "Frame description...",
      "status": "completed"
    }
  ],
  "scenes": [
    {
      "start": 0.0,
      "end": 24.097,
      "description": "Scene description..."
    }
  ]
}
```

## Format Mapping

### Frames
- **Friend's**: `frame_timestamp` → **Ours**: `timestamp_seconds` ✅ (handled)
- **Friend's**: `description` → **Ours**: `llm_response` ✅ (handled)

### Scenes
- **Friend's**: `scenes[].start/end/description` → **Ours**: `scenes[].start/end/description` ✅ (matches)

## What We're Testing

### Current Test Framework Tests:
1. ✅ Frame data (with `timestamp_seconds` or `frame_timestamp`)
2. ✅ Scene data (with `start`, `end`, `description`)
3. ✅ Transcript data (with `start`, `end`, `text`)
4. ✅ Summary (user-provided or empty)
5. ✅ Story prompt (user-provided or minimal)

### Missing from Tests:
- ❌ Friend's exact format (`frame_level_data`, `scene_level_data` structure)
- ❌ "Good moments" extraction (if friend adds this)

## "Good Moments" - Additive Enhancement

### Current Assumption:
- Friend's pipeline may add `key_moments` or `good_moments` to the data
- This would be **additive** (additional field), not replacing existing data

### Where It Would Go:
1. **In Summary**: `summary.key_moments` (already supported)
2. **In Scenes**: `scene.metadata.good_moment` or similar
3. **In Frames**: `frame.importance_score` or similar

### How to Handle:
- ✅ Summary `key_moments` is already supported in `_format_summary()`
- ⚠️ Scene metadata not yet extracted (but scenes are passed through)
- ⚠️ Frame importance not yet used (but all frames are available)

## Verification Checklist

### ✅ What's Working:
- [x] Frame loading handles both `timestamp_seconds` and `frame_timestamp`
- [x] Frame description handles both `llm_response` and `description`
- [x] Scene loading from `scene_indexes.scenes_data`
- [x] Transcript loading from `transcriptions.transcript_data`
- [x] Summary formatting with `key_moments` support
- [x] Story prompt formatting with all fields
- [x] Missing data handling (graceful defaults)

### ⚠️ What Needs Verification:
- [ ] Friend's exact JSON structure (nested `frame_level_data`, `scene_level_data`)
- [ ] How friend's data gets into database (insertion script/endpoint)
- [ ] "Good moments" format (if friend adds this)
- [ ] Scene metadata extraction (if friend adds `metadata` fields)

## Next Steps

1. **Create test with friend's exact format**:
   - Test with `frame_level_data` structure
   - Test with `scene_level_data` structure
   - Verify normalization works

2. **Add "good moments" support** (if friend adds this):
   - Extract from scene metadata
   - Extract from frame importance
   - Add to summary `key_moments`

3. **Update test framework**:
   - Add test case for friend's format
   - Verify all fields are passed to LLM correctly

## Data Flow

```
Friend's Pipeline Output
  ↓
[Insert into database]
  ↓
frames table: {timestamp_seconds, llm_response, ...}
scene_indexes table: {scenes_data: [{start, end, description}]}
transcriptions table: {transcript_data: [{start, end, text}]}
  ↓
DataLoader.load_all_data()
  ↓
[Normalize formats]
  ↓
DataCompressor.compress()
  ↓
PromptBuilder.build_storytelling_prompt()
  ↓
[Format for LLM]
  ↓
LLM receives:
- Frames: "- 0.00s: Description..."
- Scenes: "- 0.00s - 24.10s: Scene description..."
- Transcript: "- 0.00s - 2.50s: \"Text...\""
- Summary: "Summary: ..."
- Story Prompt: "Target Audience: ..."
```

## Testing Friend's Format

To test with friend's exact format, we need to:

1. **Insert friend's data into database**:
   ```python
   # Map friend's format to our database
   for frame in friend_data["frame_level_data"]:
       insert_frame({
           "video_id": video_id,
           "timestamp_seconds": frame["frame_timestamp"],
           "llm_response": frame["description"],
           "status": "completed"
       })
   
   # Insert scenes
   insert_scene_index({
       "video_id": video_id,
       "scenes_data": friend_data["scene_level_data"]["scenes"],
       "status": "completed"
   })
   ```

2. **Verify LLM receives correct format**:
   - Check prompt builder output
   - Verify timestamps are correct
   - Verify descriptions are included

3. **Test with "good moments"** (if added):
   - Extract from metadata
   - Include in summary
   - Pass to LLM

