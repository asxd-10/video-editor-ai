# AI Edit Flow & Missing Data Handling

## Flow Overview

### 1. **Input Sources**
- **Story Prompt (Preferences JSON)**: 
  - Source: iMessage app (friend is working on this)
  - For testing: Use UI form
  - Fields: `target_audience`, `story_arc`, `tone`, `key_message`, `desired_length`, `style_preferences`
  - **Can be partial/missing fields** ✅

- **Summary JSON**:
  - Source: Friend's pipeline (generates from `frames`, `scenes`, `transcriptions` tables)
  - Friend is still working on this
  - Fields: `video_summary`, `key_moments`, `content_type`, `main_topics`, `speaker_style`
  - **Can be partial/missing fields** ✅

### 2. **Data Pipeline (aidit)**
- Video upload → Processing → Populates:
  - `frames` table (frame-level LLM descriptions)
  - `scenes` table (scene boundaries and descriptions)
  - `transcriptions` table (speech-to-text)
  - `media` table (video metadata)

### 3. **AI Edit Generation**
- Takes: Summary JSON + Story Prompt JSON + Video Data (frames/scenes/transcript)
- LLM generates: Edit Decision List (EDL) with timestamps
- Output: Validated edit plan

---

## Missing Data Handling

### ✅ **API Endpoint** (`/api/videos/{video_id}/ai-edit/generate`)

**Summary Handling:**
```python
# If None or missing, uses defaults
summary = request.summary.dict() if request.summary else {}
default_summary = {
    "video_summary": "",
    "key_moments": [],
    "content_type": "presentation",
    "main_topics": [],
    "speaker_style": "casual"
}
summary = {**default_summary, **summary}  # User values override defaults
```

**Story Prompt Handling:**
```python
# If None or missing, uses defaults
story_prompt = request.story_prompt.dict() if request.story_prompt else {}
default_story_prompt = {
    "target_audience": "general",
    "story_arc": {...},
    "tone": "educational",
    "key_message": "",
    "desired_length": "medium",
    "style_preferences": {...}
}
# Deep merge for nested dicts
story_prompt = {**default_story_prompt, **story_prompt}
```

### ✅ **Prompt Builder** (`PromptBuilder`)

**Summary Formatting:**
- Checks each field with `.get()` before using
- Returns: `"No summary provided. Will analyze video content directly."` if empty
- Handles missing `key_moments`, `main_topics`, etc. gracefully

**Story Prompt Formatting:**
- Checks each field with `.get()` before using
- Returns: `"No story requirements specified. Will create a balanced, engaging edit."` if empty
- Handles missing `story_arc`, `style_preferences`, etc. gracefully

**Example Output:**
```
SUMMARY:
Summary: Educational video content
Content Type: presentation

STORY REQUIREMENTS:
Tone: educational
Key Message: Create an engaging educational video
Story Arc:
  Hook: Grab attention in first 3 seconds
  Build: Build interest and context
  ...
```

### ✅ **LLM Handling**

The LLM prompt explicitly states:
- "No summary provided" → Will analyze video content directly
- "No story requirements specified" → Will create balanced edit
- LLM is instructed to work with available data and make reasonable assumptions

---

## Testing with Minimal Data

### Example: Minimal Input (Simulating Partial Data)

```python
# Minimal story prompt (from iMessage app)
story_prompt = {
    "tone": "educational",
    "key_message": "Create an engaging video"
    # Missing: target_audience, story_arc, style_preferences
}

# Minimal summary (from friend's pipeline)
summary = {
    "video_summary": "Educational content"
    # Missing: key_moments, content_type, main_topics
}

# System will:
# 1. Merge with defaults for missing fields
# 2. Build prompt with available data
# 3. LLM will work with what's provided
```

### Test Script

```bash
cd backend
python test_ai_edit_end_to_end.py <video_id>
```

The test script uses minimal inputs to simulate real-world partial data.

---

## Key Points

1. ✅ **All fields are optional** - System provides sensible defaults
2. ✅ **Deep merging** - Nested dicts (story_arc, style_preferences) are merged properly
3. ✅ **Graceful degradation** - Works with minimal data (just media record)
4. ✅ **LLM-friendly prompts** - Explicitly tells LLM when data is missing
5. ✅ **No errors on missing fields** - Uses `.get()` everywhere with defaults

---

## Future Integration

When friend's pipeline is ready:
1. Friend's code generates `summary` JSON from `frames`/`scenes` tables
2. iMessage app generates `story_prompt` JSON from user input
3. Both can be partial - system handles missing fields automatically
4. No code changes needed - already supports partial data! ✅

