# Analysis Workflow - Complete Guide

## 🔄 What Happens When You Click "Analyze"

### **1. API Request Flow**

```
Frontend → POST /api/videos/{video_id}/analyze
         ↓
Backend API (edit.py) → Checks if already analyzed
         ↓
         → Queues Celery task: analyze_video_task.delay(video_id)
         ↓
         → Returns: {status: "queued", task_id: "..."}
```

### **2. Background Task Execution (Celery Worker)**

```
Celery Worker receives task
         ↓
analyze_video_task(video_id)
         ↓
1. Loads video from database
2. Extracts audio from video (using TranscriptionService)
3. Calls AnalysisService.analyze_video()
         ↓
AnalysisService runs:
  a) detect_silence(audio_path) → Silence segments
  b) detect_scenes(video_path) → Scene timestamps
         ↓
Stores result in: video.analysis_metadata
         ↓
Database updated: analysis_metadata = {
  "silence_segments": [(start, end), ...],
  "scene_timestamps": [timestamp1, timestamp2, ...]
}
```

---

## 📚 External Libraries Used

### **1. Silence Detection**

#### **Primary: `silero-vad`**
- **What it is:** AI-powered Voice Activity Detection (VAD) model
- **How it works:**
  - Uses PyTorch neural network to detect speech vs silence
  - Analyzes audio waveform to identify speech segments
  - Returns timestamps of when speech occurs
  - We invert this to get silence segments
- **Dependencies:**
  - `torch` (PyTorch) - CPU-only version
  - `torchaudio` - Audio loading/processing
- **Cost:** FREE (open-source, runs locally)
- **Accuracy:** High (AI-based, better than energy-based methods)

#### **Fallback: `pydub`**
- **What it is:** Audio manipulation library
- **How it works:**
  - Analyzes audio energy levels (dBFS)
  - If energy < -40 dBFS → considered silence
  - Checks every 100ms chunk
- **When used:** If `silero-vad` fails to load
- **Accuracy:** Lower (simple energy threshold)

### **2. Scene Detection**

#### **Library: `scenedetect[opencv]`**
- **What it is:** PySceneDetect - Scene change detection
- **How it works:**
  - Uses `ContentDetector` algorithm
  - Compares consecutive video frames
  - Detects significant visual changes (scene cuts)
  - Returns timestamps of scene changes
- **Dependencies:**
  - `opencv-python` (via `scenedetect[opencv]`)
  - FFmpeg (system dependency)
- **Cost:** FREE (open-source)
- **Accuracy:** Good for obvious scene cuts

### **3. Audio Extraction**

#### **Library: `ffmpeg-python`**
- **What it is:** Python wrapper for FFmpeg
- **How it works:**
  - Extracts audio track from video file
  - Converts to WAV format for analysis
  - Stored temporarily in `storage/temp/`
- **Cost:** FREE (FFmpeg is open-source)

---

## 🎯 Which Edits Require Analysis?

### **✅ REQUIRES Analysis:**

1. **Remove Silence** (`remove_silence: true`)
   - **Requires:** `analysis_metadata.silence_segments`
   - **Why:** Needs to know which segments are silence to remove them
   - **What happens without it:** 
     - If `analysis_metadata` is null → No silence removal (just aspect ratio conversion)
     - If `silence_segments` is empty → No silences detected, full video kept

2. **Scene-Based Editing** (Future feature)
   - **Requires:** `analysis_metadata.scene_timestamps`
   - **Why:** To make cuts at scene boundaries
   - **Status:** Not yet implemented

### **❌ DOES NOT Require Analysis:**

1. **Aspect Ratio Conversion** (9:16, 1:1, 16:9)
   - **Independent:** Works on any video
   - **No analysis needed**

2. **Jump Cuts** (`jump_cuts: true`)
   - **Requires:** Transcript (not analysis)
   - **Uses:** Word-level timestamps from transcription

3. **Auto Captions** (`captions: true`)
   - **Requires:** Transcript (not analysis)
   - **Uses:** Transcript segments for subtitle timing

4. **Dynamic Zoom** (`dynamic_zoom: true`)
   - **Requires:** Face detection (MediaPipe) - not analysis
   - **Status:** Placeholder (not fully implemented)

5. **Pace Optimization** (`pace_optimize: true`)
   - **Requires:** Transcript + audio analysis (future)
   - **Status:** Placeholder (not fully implemented)

---

## 📊 Data Flow Diagram

```
┌─────────────────┐
│  User Clicks    │
│  "Analyze"      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Endpoint   │
│  /analyze       │
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
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
         ┌──────────────────┐      ┌──────────────────┐
         │ Silence Detection│      │ Scene Detection  │
         │ (silero-vad)     │      │ (scenedetect)    │
         └────────┬─────────┘      └────────┬─────────┘
                  │                         │
                  │ [(0.0, 2.5), ...]       │ [10.5, 25.3, ...]
                  │                         │
                  └─────────────┬───────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │ Store in Database│
                    │ analysis_metadata│
                    └──────────────────┘
```

---

## 💾 Data Storage

### **Database Schema:**
```python
video.analysis_metadata = {
    "silence_segments": [
        (0.0, 2.5),      # Silence from 0s to 2.5s
        (15.3, 16.8),   # Silence from 15.3s to 16.8s
        (45.0, 47.2)    # Silence from 45s to 47.2s
    ],
    "scene_timestamps": [
        10.5,   # Scene change at 10.5s
        25.3,   # Scene change at 25.3s
        40.1    # Scene change at 40.1s
    ]
}
```

### **Storage Location:**
- **Database:** `videos.analysis_metadata` (JSON column in PostgreSQL)
- **Temporary Files:** `storage/temp/{video_id}/audio.wav` (deleted after analysis)

---

## ⚙️ Configuration & Parameters

### **Silence Detection:**
- **Min Silence Duration:** 600ms (0.6 seconds)
  - Only silences longer than this are detected
  - Shorter pauses are ignored (considered part of speech)
- **VAD Threshold:** 0.5 (for silero-vad)
  - Higher = more strict (fewer false positives)
  - Lower = more lenient (more false negatives)

### **Scene Detection:**
- **Threshold:** 30.0 (default)
  - Higher = fewer scene changes detected (only major cuts)
  - Lower = more scene changes (sensitive to any change)

---

## 🔍 How Editing Uses Analysis Data

### **Example: Remove Silence**

```python
# 1. Load analysis data
silence_segments = video.analysis_metadata["silence_segments"]
# → [(0.0, 2.5), (15.3, 16.8)]

# 2. Build Edit Decision List (EDL)
edl = [
    {"start": 2.5, "end": 15.3, "type": "keep"},   # Keep speech
    {"start": 15.3, "end": 16.8, "type": "skip"},  # Skip silence
    {"start": 16.8, "end": 60.0, "type": "keep"}   # Keep speech
]

# 3. FFmpeg extracts only "keep" segments
# 4. Concatenates them into final video
# Result: Video with silences removed
```

---

## 🚨 Error Handling

### **If Analysis Fails:**
1. **Silero VAD fails to load:**
   - Falls back to `pydub` energy-based detection
   - Logs warning but continues

2. **Scene detection fails:**
   - Returns empty list `[]`
   - Analysis still completes (silence detection works)

3. **Audio extraction fails:**
   - Task retries (Celery retry mechanism)
   - Max 3 retries with 60s delay

### **If Analysis Not Run:**
- **Remove Silence:** Works but finds no silences → keeps full video
- **Scene-based edits:** Not available (requires scene_timestamps)

---

## 📈 Performance

### **Typical Processing Times:**
- **Audio Extraction:** 5-10 seconds (depends on video length)
- **Silence Detection:** 10-30 seconds (depends on audio length)
- **Scene Detection:** 20-60 seconds (depends on video length)
- **Total:** ~1-2 minutes for a 10-minute video

### **Resource Usage:**
- **CPU:** High (AI model inference)
- **Memory:** ~500MB-1GB (PyTorch model)
- **Disk:** Temporary audio file (~10-50MB)

---

## 🎓 Summary

**Analysis is required for:**
- ✅ Remove Silence feature
- ✅ Future scene-based editing

**Analysis is NOT required for:**
- ❌ Aspect ratio conversion
- ❌ Jump cuts (needs transcript)
- ❌ Captions (needs transcript)
- ❌ Basic video editing

**Libraries Used:**
- `silero-vad` - AI silence detection (FREE, local)
- `scenedetect` - Scene change detection (FREE, local)
- `ffmpeg-python` - Audio extraction (FREE, local)
- `pydub` - Fallback silence detection (FREE, local)

**All analysis runs locally - no API costs!**



# What "Analysis Complete" Means for Users

## 🎯 User Value Proposition

When analysis is complete, users get:

### **1. Visual Insights Card**
- **Silence Statistics:**
  - Number of silence segments detected
  - Total silence time (e.g., "2m 15s")
  - Percentage of video that's silence (e.g., "15.3%")
- **Scene Statistics:**
  - Number of scene changes detected
  - Visual indication of major transitions

### **2. Enabled Features**

#### **✅ Remove Silence** (Now Enabled)
- **What it does:** Automatically cuts out all detected silence segments
- **User benefit:** Shorter, tighter videos without dead air
- **Example:** 11-minute video with 87 silence segments → Can save ~2-3 minutes

#### **✅ Scene-Based Editing** (Future)
- **What it does:** Makes cuts at natural scene boundaries
- **User benefit:** Smoother transitions, professional-looking edits

### **3. Disabled Features (Without Analysis)**

#### **❌ Remove Silence** (Disabled)
- Shows warning: "Run analysis first to enable silence removal"
- Checkbox is grayed out
- Tooltip explains why it's disabled

---

## 📊 What Users See

### **Before Analysis:**
```
[Analysis] Not started [Analyze Button]
```

### **After Analysis:**
```
[Analysis] Complete [Done Badge]

┌─────────────────────────────────────┐
│ 📊 Analysis Insights                │
├─────────────────────────────────────┤
│ ⏱️  Silence Detected                │
│     87 segments                     │
│     2m 15s total (15.3%)            │
│                                     │
│ 🎬 Scene Changes                    │
│     3 cuts                          │
│     Major visual transitions        │
│                                     │
│ 💡 Tip: Enable "Remove Silence" to  │
│    automatically cut out 87 silence │
│    gaps and save 2m 15s of time.   │
└─────────────────────────────────────┘

[Edit Options]
☑️ Remove Silence ✅ (now enabled)
☐ Jump Cuts (needs transcript)
☐ Auto Captions (needs transcript)
```

---

## 🎨 UI Changes Made

1. **Analysis Insights Card:**
   - Shows when analysis is complete
   - Displays silence count, total time, percentage
   - Shows scene change count
   - Includes helpful tip about using the data

2. **Feature Enablement:**
   - "Remove Silence" checkbox disabled if no analysis
   - Shows "(needs analysis)" tooltip
   - Warning message explains what's needed

3. **Status Indicators:**
   - "Analysis" button shows "Done" badge when complete
   - Clear visual feedback on what's available

---

## 💡 Realistic Textual Insights (Simple, Not AI-Generated)

**What we show (simple stats):**
- ✅ Number of silence segments
- ✅ Total silence duration
- ✅ Silence percentage
- ✅ Number of scene changes
- ✅ Actionable tip (e.g., "Enable Remove Silence to save X time")

**What we DON'T show (too complex for MVP):**
- ❌ AI-generated recommendations ("Your video has too many pauses")
- ❌ Sentiment analysis ("This section is boring")
- ❌ Retention predictions ("Viewers drop off here")
- ❌ Complex insights requiring LLM calls

**Why?**
- Simple stats are fast and reliable
- No API costs
- No additional processing time
- Clear, actionable information

---

## 🚀 User Flow

1. **User uploads video** → Video is ready
2. **User clicks "Analyze"** → Analysis runs (1-3 minutes)
3. **Analysis completes** → Insights card appears
4. **User sees:**
   - "87 silence segments detected"
   - "2m 15s of silence (15.3%)"
   - "Enable Remove Silence to save time"
5. **User enables "Remove Silence"** → Creates edit job
6. **Result:** Shorter, tighter video

---

## 📈 Value Summary

**For Users:**
- **Clear understanding** of what analysis found
- **Actionable insights** (not just data)
- **Visual feedback** on what features are available
- **Time savings** (know how much silence can be removed)

**For Us:**
- **Simple implementation** (no complex AI)
- **Fast performance** (just parsing existing data)
- **Clear UX** (users know what to do next)
- **Low maintenance** (no external APIs)

---

## 🎯 Next Steps (Future Enhancements)

If we have more time later:
1. **Visual timeline** showing silence segments
2. **Scene change previews** (thumbnails at cut points)
3. **Smart recommendations** ("This video has 30% silence - consider removing it")
4. **Comparison view** (before/after duration estimates)

But for MVP: **Simple stats + actionable tips = perfect!**

