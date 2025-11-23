# LLM Inputs - Complete Summary

## What the LLM Actually Receives

### 1. **Frames** (Visual Content Analysis)
- **Source**: `frames` table in database
- **Format Handled**:
  - ✅ Our format: `{timestamp_seconds, llm_response, status}`
  - ✅ Friend's format: `{frame_timestamp, description}` → Normalized automatically
- **Fields Used**:
  - `timestamp_seconds` (or `frame_timestamp` → normalized)
  - `llm_response` (or `description` → normalized)
- **Compression**: Max 50 frames (temporal sampling)
- **In Prompt**: `"- 0.00s: Frame description..."`

### 2. **Scenes** (Scene-Level Analysis)
- **Source**: `scene_indexes.scenes_data` (JSONB) in database
- **Format**: `{start, end, description, metadata?, scene_metadata?}`
- **Fields Used**:
  - `start` (timestamp)
  - `end` (timestamp)
  - `description` (scene description)
  - `metadata` (optional - if friend adds "good moments" here)
- **Compression**: Max 20 scenes
- **In Prompt**: `"- 0.00s - 24.10s (24.10s): Scene description..."`

### 3. **Transcript** (Speech Content)
- **Source**: `transcriptions.transcript_data` (JSONB) in database
- **Format**: `{start, end, text, words?}`
- **Fields Used**:
  - `start` (timestamp)
  - `end` (timestamp)
  - `text` (spoken text)
- **Compression**: Max 100 segments
- **In Prompt**: `"- 0.00s - 2.50s: \"Text content...\""`

### 4. **Summary** (Video Description)
- **Source**: User input (from iMessage app) OR database
- **Format**: `{video_summary, key_moments?, content_type?, main_topics?, speaker_style?}`
- **Fields Used**:
  - `video_summary` (main description)
  - `key_moments` (array of `{timestamp, description, importance}`) ← **Good moments go here**
  - `content_type` (tutorial, vlog, etc.)
  - `main_topics` (list of topics)
  - `speaker_style` (casual, professional, etc.)
- **In Prompt**: Formatted summary with key moments highlighted

### 5. **Story Prompt** (User Preferences)
- **Source**: User input (from iMessage app)
- **Format**: `{target_audience, tone, key_message, desired_length, story_arc, style_preferences}`
- **Fields Used**:
  - `target_audience` (students, general, etc.)
  - `tone` (educational, casual, etc.)
  - `key_message` (main message)
  - `desired_length` (short, medium, long)
  - `story_arc` (hook, build, climax, resolution)
  - `style_preferences` (pacing, transitions, emphasis)
- **In Prompt**: Formatted story requirements

## Friend's Pipeline Format Support

### ✅ Fully Supported

1. **Frame Format**:
   - Friend's: `{frame_timestamp, description}`
   - Normalized to: `{timestamp_seconds, llm_response}`
   - ✅ Works automatically

2. **Scene Format**:
   - Friend's: `{start, end, description, metadata, scene_metadata}`
   - Matches our format exactly
   - ✅ Works automatically

### ⚠️ "Good Moments" - Additive Enhancement

**Current Support**:
- ✅ `summary.key_moments` array is fully supported
- ✅ Formatted in prompt with timestamps and importance
- ✅ Friend can add this to summary JSON

**If Friend Adds to Scenes**:
- Scenes have `metadata` and `scene_metadata` fields
- Currently not extracted, but scenes are passed through
- **Would need**: Extract `metadata.good_moment` or similar if friend adds it

**If Friend Adds to Frames**:
- Frames could have `importance_score` or `good_moment` flag
- Currently not used, but frames are passed through
- **Would need**: Prioritize frames with `good_moment: true` in compression

## Data Flow Diagram

```
┌─────────────────────────────────────┐
│ Friend's Pipeline Output            │
│ {                                   │
│   frame_level_data: [...],          │
│   scene_level_data: {...},          │
│   (maybe good_moments)              │
│ }                                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Database Insertion                  │
│ - frames table                      │
│ - scene_indexes table               │
│ - transcriptions table              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ DataLoader.load_all_data()          │
│ - Normalizes formats                │
│ - frame_timestamp → timestamp_seconds│
│ - description → llm_response        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ DataCompressor.compress()           │
│ - Samples frames (max 50)           │
│ - Samples scenes (max 20)           │
│ - Samples transcript (max 100)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ PromptBuilder.build_storytelling_   │
│   prompt()                          │
│ - Formats all data                  │
│ - Includes summary                  │
│ - Includes story_prompt             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ LLM Receives:                      │
│ - Frames: "- 0.00s: Description"  │
│ - Scenes: "- 0.00s-24.10s: ..."   │
│ - Transcript: "- 0.00s-2.50s: ..."│
│ - Summary: "Summary: ..."          │
│ - Story Prompt: "Target: ..."      │
└─────────────────────────────────────┘
```

## Testing Status

### ✅ What We're Testing:
1. Frame format normalization (friend's → ours)
2. Scene format handling
3. Transcript format handling
4. Summary with key_moments
5. Story prompt with all fields
6. Missing data handling

### ⚠️ What We're NOT Testing Yet:
1. Friend's exact JSON structure (nested `frame_level_data`)
2. "Good moments" in scene metadata
3. "Good moments" in frame importance
4. Database insertion from friend's format

## Recommendations

### For Friend's Pipeline Integration:

1. **Database Insertion**:
   - Map `frame_level_data` → `frames` table
   - Map `scene_level_data.scenes` → `scene_indexes.scenes_data`
   - Ensure `status = 'completed'` for both

2. **"Good Moments" Enhancement**:
   - **Option A**: Add to `summary.key_moments` (already supported)
   - **Option B**: Add to scene `metadata.good_moment` (needs extraction)
   - **Option C**: Add to frame `importance_score` (needs prioritization)

3. **Format Verification**:
   - Run `test_friend_format.py` to verify normalization
   - Check prompt output to ensure all data is included

## Quick Test

```bash
# Test format compatibility
python test_friend_format.py

# Test with real data (after friend's data is in DB)
python test_llm_quality.py {video_id}
```

## Summary

✅ **LLM receives**:
- Frames (normalized from friend's format)
- Scenes (matches friend's format)
- Transcript (standard format)
- Summary (with key_moments support)
- Story Prompt (user preferences)

✅ **Format compatibility**: Fully supported
✅ **"Good moments"**: Supported via `summary.key_moments` (additive)
⚠️ **Future enhancement**: Extract from scene/frame metadata if friend adds it

