# Transcription Workflow - Complete Guide

## 🔄 What Happens When You Click "Transcribe"

### **1. API Request Flow**

```
Frontend → POST /api/videos/{video_id}/transcribe
         ↓
Backend API (edit.py) → Checks if transcript exists
         ↓
         → Queues Celery task: transcribe_video_task.delay(video_id)
         ↓
         → Returns: {status: "queued", task_id: "..."}
```

### **2. Background Task Execution (Celery Worker)**

```
Celery Worker receives task
         ↓
transcribe_video_task(video_id)
         ↓
1. Loads video from database
2. Extracts audio from video (FFmpeg → WAV, 16kHz mono)
3. Loads Whisper model (if not already loaded)
4. Transcribes audio with word-level timestamps
5. Converts to structured format
6. Saves to database: transcripts table
```

---

## 📚 Library & Model Used

### **Library: `faster-whisper`**
- **What it is:** Optimized implementation of OpenAI's Whisper model
- **Why faster-whisper?**
  - 4x faster than original Whisper
  - Lower memory usage
  - Better CPU performance
  - Same accuracy as OpenAI Whisper
- **Cost:** FREE (open-source, runs locally)
- **License:** MIT (commercial use allowed)

### **Model: `base`**
- **Size:** ~150MB (downloads automatically on first use)
- **Device:** CPU (no GPU required)
- **Compute Type:** int8 (quantized for speed)
- **Speed vs Accuracy Trade-off:**
  - `tiny`: Fastest, lowest accuracy (~30% WER)
  - `base`: **Current** - Good balance (~20% WER, ~2-3x real-time)
  - `small`: Better accuracy (~15% WER, ~1x real-time)
  - `medium`: High accuracy (~10% WER, ~0.5x real-time)
  - `large`: Best accuracy (~5% WER, ~0.3x real-time)

### **Why `base` Model?**
- **Hackathon constraint:** Need speed
- **Good enough accuracy:** ~80% word accuracy
- **Fast processing:** 2-3x real-time (11min video = ~4-5min transcription)
- **CPU-friendly:** Works on any machine

---

## 📊 Output Format

### **Database Storage: `transcripts` Table**

```sql
CREATE TABLE transcripts (
    id VARCHAR(36) PRIMARY KEY,
    video_id VARCHAR(36) UNIQUE,
    segments JSON,           -- Array of transcript segments
    language VARCHAR(10),    -- Detected language (e.g., "en")
    confidence JSON,         -- Overall confidence metrics
    created_at VARCHAR
);
```

### **Segments Structure (JSON)**

```json
{
  "segments": [
    {
      "start": 0.0,           // Start time in seconds
      "end": 4.5,             // End time in seconds
      "text": "Hello, welcome to this video tutorial.",
      "confidence": -0.23,     // Log probability (higher = more confident)
      "words": [
        {
          "word": "Hello",
          "start": 0.0,
          "end": 0.5,
          "probability": 0.95
        },
        {
          "word": "welcome",
          "start": 0.6,
          "end": 1.1,
          "probability": 0.92
        },
        // ... more words
      ]
    },
    {
      "start": 4.5,
      "end": 8.2,
      "text": "Today we're going to learn about video editing.",
      "confidence": -0.18,
      "words": [...]
    }
    // ... more segments
  ],
  "language": "en",
  "confidence": {
    "avg_logprob": -0.20,
    "language_probability": 0.99
  }
}
```

### **Key Features:**
- **Segment-level:** Natural speech segments (sentences/phrases)
- **Word-level timestamps:** Precise timing for each word
- **Confidence scores:** Per-segment and per-word confidence
- **Language detection:** Auto-detects language (we force "en" for speed)

---

## 💾 Where It's Stored

### **Database:**
- **Table:** `transcripts`
- **Column:** `segments` (JSON)
- **Relationship:** One transcript per video (`video_id` unique)

### **Temporary Files:**
- **Audio extraction:** `storage/temp/{video_id}/audio.wav`
- **Format:** 16kHz mono WAV (Whisper's preferred format)
- **Size:** ~1-2MB per minute of video
- **Cleanup:** Not automatically deleted (can be reused)

---

## 🎯 Which Edit Features Require Transcription?

### **✅ REQUIRES Transcript:**

1. **Jump Cuts** (`jump_cuts: true`)
   - **Why:** Needs word-level timestamps to make precise cuts
   - **How it works:**
     - Groups words into phrases
     - Removes gaps > 0.5s between words
     - Creates cuts at word boundaries
   - **What happens without it:**
     - Feature is disabled
     - Warning: "Jump cuts disabled: transcript not available"

2. **Auto Captions** (`captions: true`)
   - **Why:** Needs transcript text and timestamps
   - **How it works:**
     - Generates SRT subtitle file from segments
     - Burns captions into video using FFmpeg
   - **What happens without it:**
     - Feature is disabled
     - Warning: "Captions disabled: transcript not available"

3. **Clip Candidates Generation**
   - **Why:** Needs transcript to find high-energy segments, keywords, hooks
   - **How it works:**
     - Analyzes speech density
     - Finds keyword-rich segments
     - Identifies potential hooks
   - **What happens without it:**
     - Cannot generate clip candidates
     - Error: "Transcript not found. Transcribe video first."

### **❌ DOES NOT Require Transcript:**

1. **Remove Silence** (`remove_silence: true`)
   - **Works with:** Analysis (silence detection)
   - **Can work without transcript:** Uses silence segments directly

2. **Aspect Ratio Conversion** (9:16, 1:1, 16:9)
   - **Independent:** Works on any video

3. **Dynamic Zoom** (`dynamic_zoom: true`)
   - **Requires:** Face detection (not transcript)

4. **Pace Optimization** (`pace_optimize: true`)
   - **Future:** Would use transcript + audio analysis

---

## ⚡ Speed & Performance

### **Processing Speed:**
- **Model:** `base` (CPU, int8)
- **Speed:** ~2-3x real-time
- **Example:**
  - 11-minute video → ~4-5 minutes transcription
  - 60-minute video → ~20-30 minutes transcription

### **Factors Affecting Speed:**
1. **Video length:** Linear scaling
2. **CPU performance:** Faster CPU = faster transcription
3. **Model size:** `base` is fastest good-quality model
4. **Language:** Specifying "en" is faster than auto-detect

### **Memory Usage:**
- **Model loading:** ~500MB RAM
- **Audio buffer:** ~50-100MB per minute
- **Total:** ~1-2GB for typical videos

### **First Run:**
- **Model download:** ~150MB (one-time, cached)
- **Download time:** ~30 seconds (depends on internet)

---

## 🎯 Quality & Accuracy

### **Word Error Rate (WER):**
- **Base model:** ~20% WER
- **What this means:**
  - 80% of words are correct
  - 20% may have errors (misheard words, punctuation issues)
  - Generally good for editing purposes

### **Strengths:**
- ✅ Handles natural speech well
- ✅ Good with accents (if trained)
- ✅ Handles background noise reasonably
- ✅ Word-level timestamps are accurate

### **Weaknesses:**
- ❌ May miss proper nouns
- ❌ Can struggle with technical terms
- ❌ Punctuation is sometimes off
- ❌ May split/merge words incorrectly

### **For Editing Use Cases:**
- **Good enough for:**
  - Jump cuts (word boundaries are accurate)
  - Captions (minor errors acceptable)
  - Clip selection (can find keywords)
- **Not perfect for:**
  - Legal transcription (needs 99%+ accuracy)
  - Medical transcription (needs specialized models)

---

## 🔍 How Editing Uses Transcript

### **1. Jump Cuts Example:**

```python
# Transcript segments:
[
  {"start": 0.0, "end": 2.5, "text": "Hello, welcome...", "words": [...]},
  {"start": 5.0, "end": 7.2, "text": "Today we'll learn...", "words": [...]},
  # Gap from 2.5 to 5.0 (2.5s silence)
]

# Jump cuts logic:
# - Keep: 0.0-2.5s (first segment)
# - Skip: 2.5-5.0s (gap > 0.5s)
# - Keep: 5.0-7.2s (second segment)

# Result: Video jumps from 2.5s to 5.0s (removes silence)
```

### **2. Captions Example:**

```python
# Transcript segment:
{
  "start": 0.0,
  "end": 4.5,
  "text": "Hello, welcome to this video tutorial."
}

# SRT file generated:
1
00:00:00,000 --> 00:00:04,500
Hello, welcome to this video tutorial.

# FFmpeg burns this into video
```

### **3. Clip Selection Example:**

```python
# Transcript segments analyzed:
- High speech density: 10.0-25.0s (many words, little silence)
- Keywords found: "tutorial", "learn", "editing" at 15.0s
- Hook candidate: "Welcome to this amazing tutorial" at 10.0s

# Clip candidate generated:
{
  "start": 10.0,
  "end": 25.0,
  "score": 85,
  "hook_text": "Welcome to this amazing tutorial"
}
```

---

## 📈 Data Flow Diagram

```
┌─────────────────┐
│  User Clicks    │
│  "Transcribe"   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Endpoint   │
│  /transcribe    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Celery Queue   │─────▶│  Worker Process  │
│  (Redis)        │      │  (Background)    │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Extract Audio    │
                         │ (FFmpeg)         │
                         │ → 16kHz mono    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Load Whisper     │
                         │ Model (base)     │
                         │ (~150MB, cached) │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Transcribe Audio │
                         │ (faster-whisper) │
                         │ → Segments       │
                         │ → Word timestamps│
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │ Convert to JSON Format   │
                    │ - Segment-level          │
                    │ - Word-level             │
                    │ - Confidence scores      │
                    └────────┬─────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Store in Database│
                    │ transcripts table│
                    └──────────────────┘
```

---

## 🚨 Error Handling

### **If Transcription Fails:**
1. **Audio extraction fails:**
   - Task retries (Celery retry mechanism)
   - Max 3 retries with 60s delay

2. **Whisper model fails:**
   - Falls back to error handling
   - Logs error for debugging

3. **Database save fails:**
   - Transaction rolls back
   - Task retries

### **If Transcript Not Available:**
- **Jump Cuts:** Disabled, shows warning
- **Captions:** Disabled, shows warning
- **Clip Candidates:** Returns 400 error
- **Other edits:** Work normally (silence removal, aspect ratio)

---

## 💡 Model Comparison

| Model | Size | Speed | WER | Use Case |
|-------|------|-------|-----|----------|
| `tiny` | 75MB | 5x | ~30% | Fastest, lowest quality |
| `base` | 150MB | **2-3x** | **~20%** | **Current - Good balance** |
| `small` | 500MB | 1x | ~15% | Better quality, slower |
| `medium` | 1.5GB | 0.5x | ~10% | High quality, very slow |
| `large` | 3GB | 0.3x | ~5% | Best quality, extremely slow |

**For hackathon:** `base` is perfect - fast enough, accurate enough.

---

## 🎓 Summary

**Library:** `faster-whisper` (free, open-source)
**Model:** `base` (CPU, int8 quantization)
**Speed:** 2-3x real-time (11min video = ~4-5min transcription)
**Accuracy:** ~80% word accuracy (good enough for editing)
**Output:** Segments with word-level timestamps
**Storage:** PostgreSQL JSON column
**Cost:** FREE (runs locally, no API costs)

**Features that require transcript:**
- ✅ Jump Cuts
- ✅ Auto Captions
- ✅ Clip Candidates

**Features that don't require transcript:**
- ❌ Remove Silence (uses analysis instead)
- ❌ Aspect Ratio Conversion
- ❌ Dynamic Zoom

**All transcription runs locally - no API costs!**

