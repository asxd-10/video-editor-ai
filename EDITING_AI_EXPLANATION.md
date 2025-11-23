# Current Editing Logic & AI Roadmap

## 🔍 Current State: What We Have Now

### **Current Editing is Rule-Based (NOT AI-Driven)**

Right now, our editing system uses **heuristic/rule-based logic**, not AI. Here's what's happening:

#### 1. **Transcription** ✅ (AI-Powered)
- **Model:** `faster-whisper` (Whisper model - AI)
- **What it does:** Converts speech to text with word-level timestamps
- **Status:** ✅ Fully implemented and working

#### 2. **Silence Detection** ✅ (AI-Powered)
- **Model:** `silero-vad` (Voice Activity Detection - AI)
- **What it does:** Detects silent segments in audio
- **Status:** ✅ Fully implemented with fallback

#### 3. **Scene Detection** ✅ (Computer Vision)
- **Library:** `scenedetect` (PySceneDetect)
- **What it does:** Detects scene changes using content analysis
- **Status:** ✅ Fully implemented

#### 4. **Clip Selection** ⚠️ (Rule-Based, NOT AI)
- **Current Logic:** Heuristic-based
  - High speech density segments
  - Keyword matching (simple text search)
  - Scene change boundaries
  - **No AI understanding of content quality**
- **Status:** ✅ Works but not intelligent

#### 5. **Editing Decisions** ⚠️ (Rule-Based, NOT AI)
- **Current Logic:**
  - Remove silence: Simple gap detection
  - Jump cuts: Remove gaps > 0.5s between words
  - Captions: Direct transcript burn-in
  - **No understanding of pacing, retention, or engagement**
- **Status:** ✅ Works but basic

---

## 🤖 What AI Models We're Currently Using

### **Active AI Models:**
1. **Whisper (via faster-whisper)**
   - Purpose: Speech-to-text transcription
   - Type: Neural network (Transformer-based)
   - Cost: Free (runs locally)

2. **Silero VAD**
   - Purpose: Voice activity detection
   - Type: Neural network
   - Cost: Free (runs locally)

### **Available but NOT Used Yet:**
3. **Transformers (HuggingFace)**
   - Status: Installed but not integrated
   - Could use: Mistral, Llama, etc. for content understanding

---

## 🚀 Roadmap: Making It AI-Driven

### **Phase 1: LLM Integration for Content Understanding** (Next Step)

#### **What We Need:**
```python
# New service: backend/app/services/llm_service.py
class LLMService:
    def analyze_content_quality(self, transcript, timestamps):
        """Use LLM to score segments for engagement"""
        # Prompt: "Rate this video segment 1-10 for viewer retention"
        
    def generate_hook(self, transcript):
        """Find the most engaging opening line"""
        # Prompt: "What's the best hook from this transcript?"
        
    def optimize_captions(self, transcript, platform):
        """Rewrite captions for TikTok vs YouTube vs LinkedIn"""
        # Prompt: "Rewrite these captions for TikTok style"
```

#### **Implementation Plan:**
1. **Choose LLM:**
   - **Option A (Free):** HuggingFace Inference API (free tier)
   - **Option B (Better):** OpenAI GPT-4o-mini ($0.15/1M tokens)
   - **Option C (Best):** Local model via `transformers` (Mistral-7B)

2. **Add LLM Service:**
   ```python
   # backend/app/services/llm_service.py
   from transformers import pipeline
   # or
   from openai import OpenAI
   ```

3. **Enhance Clip Selection:**
   - Current: Rule-based (speech density, keywords)
   - **AI-Enhanced:** LLM scores each segment for:
     - Engagement potential
     - Hook quality
     - Retention likelihood
     - Platform fit (TikTok vs YouTube)

4. **Enhance Editing:**
   - Current: Remove silence, jump cuts at gaps
   - **AI-Enhanced:** LLM decides:
     - Which silences to keep (dramatic pauses)
     - Optimal cut points (not just gaps)
     - Pacing adjustments per segment
     - Caption timing and style

---

### **Phase 2: Prompt-Based Editing** (Your Friend's Goal)

#### **The Vision:**
User types: *"Make this video TikTok-ready with fast cuts and energetic captions"*

**What happens:**
1. LLM parses the prompt
2. LLM generates edit instructions:
   ```json
   {
     "remove_silence": true,
     "jump_cuts": true,
     "pace_multiplier": 1.2,
     "caption_style": "energetic",
     "aspect_ratio": "9:16",
     "cut_points": [2.3, 5.7, 8.1, ...]  // AI-decided
   }
   ```
3. EditorService applies these instructions

#### **Implementation:**
```python
# backend/app/services/prompt_editor.py
class PromptEditor:
    def parse_edit_prompt(self, user_prompt: str, video_context: dict):
        """Convert natural language to edit instructions"""
        llm_prompt = f"""
        User wants: {user_prompt}
        Video: {video_context['duration']}s, {video_context['transcript']}
        
        Generate edit instructions in JSON format:
        {{
            "remove_silence": bool,
            "jump_cuts": bool,
            "pace_multiplier": float,
            "caption_style": str,
            "aspect_ratios": [str],
            "cut_points": [float],
            "zoom_points": [float]
        }}
        """
        return llm_service.generate(llm_prompt)
```

---

### **Phase 3: Advanced AI Features**

1. **Retention Prediction:**
   - Train/fine-tune model on retention data
   - Predict which segments will lose viewers
   - Auto-remove low-retention segments

2. **Emotion Detection:**
   - Analyze audio tone (excited, calm, etc.)
   - Adjust pacing based on emotion
   - Match music/effects to emotion

3. **Visual AI:**
   - Face detection (already have mediapipe)
   - Object tracking for dynamic zoom
   - Scene composition analysis

---

## 📊 Current vs AI-Enhanced Comparison

| Feature | Current (Rule-Based) | AI-Enhanced (Future) |
|---------|---------------------|---------------------|
| **Clip Selection** | Speech density, keywords | LLM scores for engagement |
| **Cut Points** | Gaps > 0.5s | LLM decides optimal cuts |
| **Silence Removal** | Remove all silences | LLM keeps dramatic pauses |
| **Captions** | Direct transcript | LLM rewrites per platform |
| **Pacing** | Fixed rules | LLM adjusts per segment |
| **Hook Generation** | First sentence | LLM finds best hook |
| **Prompt Editing** | ❌ Not supported | ✅ Natural language → edits |

---

## 🎯 Immediate Next Steps for AI Integration

### **Step 1: Add LLM Service** (1-2 hours)
```python
# backend/app/services/llm_service.py
class LLMService:
    def __init__(self):
        # Option 1: HuggingFace (free)
        self.pipeline = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.2")
        
        # Option 2: OpenAI (better, costs money)
        # self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def analyze_segment(self, text, context):
        prompt = f"Rate this video segment for engagement: {text}"
        return self.pipeline(prompt)
```

### **Step 2: Enhance ClipSelector** (2-3 hours)
```python
# In clip_selector.py
def generate_candidates(self, video_id, db):
    # ... existing heuristic logic ...
    
    # NEW: Score with LLM
    for candidate in candidates:
        score = llm_service.score_engagement(
            candidate['hook_text'],
            candidate['transcript_segment']
        )
        candidate['llm_score'] = score
        candidate['final_score'] = (candidate['score'] * 0.6) + (score * 0.4)
```

### **Step 3: Add Prompt Parser** (3-4 hours)
```python
# New endpoint: POST /api/videos/{video_id}/edit/prompt
@router.post("/{video_id}/edit/prompt")
async def create_edit_from_prompt(
    video_id: str,
    prompt: str,  # "Make this TikTok-ready"
    db: Session = Depends(get_db)
):
    # Parse prompt with LLM
    edit_instructions = prompt_editor.parse(prompt, video_context)
    
    # Create edit job with AI-generated instructions
    edit_job = EditJob(edit_options=edit_instructions)
    # ...
```

---

## 💡 Key Insight

**Current System:**
- ✅ Works reliably
- ✅ Fast (no API calls)
- ❌ Not intelligent
- ❌ Can't understand user intent

**AI-Enhanced System:**
- ✅ Understands content quality
- ✅ Adapts to user prompts
- ✅ Platform-specific optimization
- ⚠️ Requires LLM API (cost or setup)
- ⚠️ Slower (API calls)

**Best Approach:**
- Keep rule-based as fallback
- Add AI layer on top
- Use AI for "smart" decisions
- Use rules for "fast" decisions

---

## 🔧 Technical Details

### **Current Architecture:**
```
User → EditJobManager → EditorService → FFmpeg
                          ↓
                    (Rule-based EDL)
```

### **AI-Enhanced Architecture:**
```
User → EditJobManager → PromptEditor → LLMService
                          ↓              ↓
                    EditorService ← AI Instructions
                          ↓
                       FFmpeg
```

---

## 📝 Summary

**What you have now:**
- Rule-based editing (works, but not smart)
- AI transcription (Whisper)
- AI silence detection (Silero VAD)

**What you need for AI-driven editing:**
1. LLM integration (HuggingFace or OpenAI)
2. Prompt parsing service
3. AI-enhanced clip scoring
4. AI-generated edit instructions

**Your friend's goal (prompt-based editing):**
- This is Phase 2 of the roadmap
- Requires LLM service first
- Then prompt parser
- Then integration with EditorService

The foundation is ready - you just need to add the AI layer! 🚀

