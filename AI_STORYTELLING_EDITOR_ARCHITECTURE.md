# AI Storytelling Editor - Architecture & Plan

## 🎯 What You're Building

A **separate AI-driven editing page** that uses an LLM agent to create storytelling edits based on:
- **Visual understanding** (frame-level LLM responses from `frames` table)
- **Speech understanding** (transcript data from `transcriptions` table)
- **User intent** (story prompt + summary/description)
- **Output:** Edit Decision List (EDL) that creates a narrative video with smooth transitions

---

## 📊 Data Sources (Already Populated)

### **1. `media` Table**
```sql
- video_id (text) - Links to your existing videos
- video_url (text) - Video file location
- media_type (text) - 'video'
```

### **2. `transcriptions` Table**
```sql
- video_id (text)
- transcript_data (JSONB) - Full transcript with segments
- transcript_text (text) - Plain text transcript
- segment_count (integer)
- status (text) - 'pending', 'complete', 'failed'
```

### **3. `frames` Table**
```sql
- video_id (bigint) - References media.id
- frame_number (integer)
- timestamp_seconds (double precision)
- llm_response (text) - LLM analysis of this frame
- status (text) - 'pending', 'complete', 'failed'
```

**Key Insight:** Each frame has an LLM response describing what's happening visually at that timestamp.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    New AI Editor Page                        │
│  (Separate route: /video/{video_id}/ai-edit)                │
└───────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              User Inputs (Structured)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Summary/Description (LLM-generated or user-provided)│   │
│  │ - Video content summary                              │   │
│  │ - Key moments identified                             │   │
│  │ - Context and background                             │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Story Prompt (User's desired narrative)              │   │
│  │ - Target audience                                    │   │
│  │ - Story arc (hook, build, climax, resolution)         │   │
│  │ - Tone/style (educational, entertaining, dramatic)    │   │
│  │ - Key message/theme                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Agent (Gemini 3 Pro Image Preview)          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Inputs:                                              │   │
│  │ 1. Frame-level visual descriptions (from frames)    │   │
│  │ 2. Transcript segments with timestamps               │   │
│  │ 3. Summary/Description                              │   │
│  │ 4. Story Prompt                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Agent Reasoning:                                     │   │
│  │ - Analyzes visual + speech content                   │   │
│  │ - Maps to story arc (hook, build, climax)            │   │
│  │ - Identifies key moments                              │   │
│  │ - Plans transitions between scenes                   │   │
│  │ - Creates narrative flow                              │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Output: Structured Edit Plan (JSON)                     │   │
│  │ {                                                      │   │
│  │   "story_arc": {hook, build, climax, resolution},     │   │
│  │   "key_moments": [{timestamp, description, importance}],│
│  │   "transitions": [{from, to, type, reason}],          │   │
│  │   "edl": [{start, end, type, reason}]                 │   │
│  │ }                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Edit Execution (Reuse Existing Editor)         │
│  - Takes EDL from LLM agent                                  │
│  - Uses EditorService to render final video                  │
│  - Applies transitions, pacing, effects                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Structured Input Format

### **1. Summary/Description Structure**

```json
{
  "video_summary": "Brief overview of video content",
  "key_moments": [
    {
      "timestamp": 10.5,
      "description": "Introduction of main topic",
      "importance": "high"
    }
  ],
  "content_type": "tutorial|interview|presentation|vlog",
  "main_topics": ["topic1", "topic2"],
  "duration_seconds": 664.0,
  "speaker_style": "formal|casual|energetic"
}
```

### **2. Story Prompt Structure**

```json
{
  "target_audience": "students|professionals|general",
  "story_arc": {
    "hook": "Grab attention in first 3 seconds",
    "build": "Build interest and context",
    "climax": "Main point/revelation",
    "resolution": "Conclusion/call-to-action"
  },
  "tone": "educational|entertaining|dramatic|inspirational",
  "key_message": "Main takeaway for viewers",
  "desired_length": "short|medium|long",
  "style_preferences": {
    "pacing": "fast|moderate|slow",
    "transitions": "smooth|dynamic|minimal",
    "emphasis": "visual|audio|balanced"
  }
}
```

---

## 🤖 LLM Agent Design

### **Agent Prompt Structure**

```
You are an expert video editor AI that creates storytelling edits.

VIDEO CONTEXT:
- Summary: {summary}
- Duration: {duration}s
- Content Type: {content_type}

STORY REQUIREMENTS:
- Target Audience: {target_audience}
- Story Arc: {story_arc}
- Tone: {tone}
- Key Message: {key_message}

VISUAL CONTENT (Frame Analysis):
{frame_data}
- Frame at {timestamp}s: {llm_response}
- Frame at {timestamp}s: {llm_response}
...

SPEECH CONTENT (Transcript):
{transcript_segments}
- {start}s - {end}s: "{text}"
...

TASK:
1. Analyze visual and speech content
2. Map content to story arc (hook, build, climax, resolution)
3. Identify key moments that support the narrative
4. Plan smooth transitions between scenes
5. Create Edit Decision List (EDL) with timestamps

OUTPUT FORMAT (JSON):
{
  "story_analysis": {
    "hook_timestamp": 10.5,
    "climax_timestamp": 300.0,
    "resolution_timestamp": 600.0
  },
  "key_moments": [
    {
      "start": 10.5,
      "end": 25.0,
      "importance": "high",
      "reason": "Strong hook with visual impact",
      "story_role": "hook"
    }
  ],
  "transitions": [
    {
      "from_timestamp": 25.0,
      "to_timestamp": 30.0,
      "type": "cut|fade|zoom",
      "reason": "Smooth transition to next scene"
    }
  ],
  "edl": [
    {
      "start": 10.5,
      "end": 25.0,
      "type": "keep",
      "reason": "Hook moment - grabs attention"
    },
    {
      "start": 25.0,
      "end": 30.0,
      "type": "transition",
      "transition_type": "fade",
      "duration": 0.5
    },
    {
      "start": 30.0,
      "end": 120.0,
      "type": "keep",
      "reason": "Build context and interest"
    }
  ],
  "recommendations": [
    "Add music at 10.5s for emotional impact",
    "Speed up section 30-60s by 10% for pacing"
  ]
}
```

---

## 🔌 API Integration (OpenRouter)

### **Configuration**

```python
# backend/app/config.py
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_KEY")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
MODEL_NAME: str = "google/gemini-3-pro-image-preview"  # Supports vision
```

### **Why Gemini 3 Pro Image Preview?**
- **Vision capabilities:** Can analyze frames if needed
- **Large context:** Handles long transcripts + frame data
- **Structured output:** Good at JSON generation
- **Cost-effective:** Via OpenRouter

---

## 📁 New Files Structure

```
backend/
├── app/
│   ├── models/
│   │   └── ai_edit_job.py          # New: AI edit job tracking
│   ├── services/
│   │   ├── llm_agent.py            # New: LLM agent service
│   │   └── storytelling_editor.py  # New: Storytelling edit logic
│   ├── api/
│   │   └── ai_edit.py              # New: AI edit endpoints
│   └── workers/
│       └── tasks.py                # Add: ai_edit_job_task

frontend/
├── src/
│   ├── pages/
│   │   └── AIStoryEditor.jsx       # New: AI editor page
│   ├── components/
│   │   └── ai/
│   │       ├── StoryPromptForm.jsx # New: Story prompt input
│   │       ├── SummaryView.jsx     # New: Summary display
│   │       ├── AIEditPreview.jsx   # New: Preview EDL
│   │       └── StoryArcVisualizer.jsx # New: Visual story arc
```

---

## 🔄 Data Flow

### **Step 1: Load Data**
```
1. User navigates to /video/{video_id}/ai-edit
2. Backend loads:
   - media record (video_url)
   - transcriptions record (transcript_data, transcript_text)
   - frames records (all frames with llm_response)
3. Frontend displays:
   - Summary/Description (editable)
   - Story Prompt form (user input)
```

### **Step 2: User Input**
```
1. User fills Story Prompt form:
   - Target audience
   - Story arc preferences
   - Tone/style
   - Key message
2. User can edit Summary/Description
3. User clicks "Generate AI Edit"
```

### **Step 3: LLM Agent Processing**
```
1. Backend constructs agent prompt:
   - Combines frame data (visual)
   - Combines transcript data (speech)
   - Adds summary/description
   - Adds story prompt
2. Calls OpenRouter API (Gemini 3 Pro)
3. LLM returns structured edit plan (JSON)
4. Backend validates and stores EDL
```

### **Step 4: Edit Execution**
```
1. Backend converts LLM EDL to EditorService format
2. Uses existing EditorService to render video
3. Applies transitions, pacing, effects
4. Returns edited video
```

---

## 🎨 Frontend Page Structure

### **Route:** `/video/:videoId/ai-edit`

### **Layout:**
```
┌─────────────────────────────────────────────────────┐
│  AI Storytelling Editor                              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  [Video Preview]                                     │
│                                                       │
├─────────────────────────────────────────────────────┤
│  Summary & Context                                   │
│  ┌─────────────────────────────────────────────┐   │
│  │ [Editable summary/description]               │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  Story Prompt                                        │
│  ┌─────────────────────────────────────────────┐   │
│  │ Target Audience: [Dropdown]                  │   │
│  │ Story Arc: [Hook/Build/Climax/Resolution]   │   │
│  │ Tone: [Educational/Entertaining/...]         │   │
│  │ Key Message: [Text input]                    │   │
│  │ Desired Length: [Short/Medium/Long]          │   │
│  │ [Generate AI Edit Button]                    │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  AI Edit Plan (After Generation)                    │
│  ┌─────────────────────────────────────────────┐   │
│  │ Story Arc Visualization                      │   │
│  │ [Timeline with hook/climax markers]          │   │
│  │                                               │   │
│  │ Key Moments                                  │   │
│  │ - 10.5s: Hook moment (high importance)       │   │
│  │ - 300s: Climax (main point)                   │   │
│  │                                               │   │
│  │ Transitions                                  │   │
│  │ - 25s → 30s: Fade (smooth)                   │   │
│  │                                               │   │
│  │ [Preview] [Edit] [Apply]                      │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Plan

### **Phase 1: Data Models & API Setup**
1. Create `AIEditJob` model (similar to `EditJob` but with LLM context)
2. Create API endpoints:
   - `GET /api/videos/{video_id}/ai-edit/data` - Load media/transcriptions/frames
   - `POST /api/videos/{video_id}/ai-edit/generate` - Trigger LLM agent
   - `GET /api/videos/{video_id}/ai-edit/plan` - Get generated edit plan
   - `POST /api/videos/{video_id}/ai-edit/apply` - Apply edit plan

### **Phase 2: LLM Agent Service**
1. Create `LLMAgentService`:
   - Constructs prompts from data
   - Calls OpenRouter API
   - Parses structured JSON response
   - Validates EDL format
2. Create `StorytellingEditorService`:
   - Converts LLM EDL to EditorService format
   - Handles transitions
   - Applies pacing adjustments

### **Phase 3: Frontend Page**
1. Create `AIStoryEditor` page component
2. Create form components:
   - `StoryPromptForm` - Structured input
   - `SummaryEditor` - Editable summary
3. Create visualization components:
   - `StoryArcVisualizer` - Timeline with story markers
   - `AIEditPreview` - Preview EDL before applying

### **Phase 4: Integration**
1. Connect to existing `EditorService`
2. Reuse video rendering pipeline
3. Add download/preview functionality

---

## 💰 Cost Estimation (OpenRouter)

### **Gemini 3 Pro Image Preview Pricing:**
- **Input:** ~$0.50 per 1M tokens
- **Output:** ~$1.50 per 1M tokens

### **Typical Request:**
- **Input tokens:** ~5,000-10,000 (frames + transcript + prompt)
- **Output tokens:** ~1,000-2,000 (structured JSON)
- **Cost per edit:** ~$0.01-0.02

**Very affordable for hackathon!**

---

## 🎯 Key Design Decisions

### **1. Separate Page vs. Tab**
- **Decision:** Separate page (`/video/:id/ai-edit`)
- **Reason:** Different workflow, different data sources, cleaner separation

### **2. LLM Model Choice**
- **Decision:** Gemini 3 Pro Image Preview
- **Reason:** Vision capabilities, large context, structured output, cost-effective

### **3. Structured Inputs**
- **Decision:** JSON schema for Summary and Story Prompt
- **Reason:** Better LLM understanding, easier validation, consistent output

### **4. EDL Format**
- **Decision:** Reuse existing EDL format from `EditorService`
- **Reason:** No need to rewrite rendering logic, proven format

### **5. Agent vs. Direct LLM Call**
- **Decision:** Single LLM call with structured prompt (not multi-step agent)
- **Reason:** Simpler, faster, cheaper, sufficient for MVP

---

## 📋 Next Steps

1. **Review & Approve Architecture** ✅
2. **Create Database Models** (AIEditJob)
3. **Create LLM Agent Service** (OpenRouter integration)
4. **Create API Endpoints** (Data loading, generation, application)
5. **Create Frontend Page** (Story prompt form, visualization)
6. **Test End-to-End** (Generate edit → Preview → Apply)

---

## 🚀 MVP Scope

**Must Have:**
- ✅ Load data from existing tables
- ✅ Story prompt form
- ✅ LLM agent generates EDL
- ✅ Preview edit plan
- ✅ Apply edit (reuse EditorService)

**Nice to Have:**
- ⏳ Edit plan visualization
- ⏳ Multiple story templates
- ⏳ A/B testing different edits
- ⏳ Export edit plan as JSON

**Future:**
- 🔮 Multi-step agent (plan → refine → execute)
- 🔮 Real-time preview
- 🔮 Collaborative editing

---

## ❓ Questions to Consider

1. **Frame Data:** How many frames are analyzed? All frames or sampled?
2. **Transcript:** Full transcript or key segments?
3. **LLM Context:** What's the max context window? (Gemini 3 Pro: ~1M tokens)
4. **Caching:** Should we cache LLM responses for same video?
5. **Error Handling:** What if LLM returns invalid EDL?

---

## 📝 Summary

You're building a **storytelling-focused AI editor** that:
- Uses visual (frames) + speech (transcript) understanding
- Takes user's story intent (prompt)
- Generates narrative-driven edits
- Reuses existing rendering pipeline

**Key Innovation:** Combining frame-level visual understanding with transcript understanding to create story-driven edits, not just technical edits.

