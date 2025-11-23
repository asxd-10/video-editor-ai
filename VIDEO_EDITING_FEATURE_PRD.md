# Video Editing Feature - Product Requirements Document (PRD)

## Executive Summary

This document defines the core requirements and implementation plan for the **AI-Powered Video Editing Feature** - the primary differentiator for our hackathon project. This feature transforms uploaded videos into platform-optimized, engagement-maximized short-form content using AI.

**Target USPs:**
- **USP #2:** Retention Optimization Editing
- **USP #3:** Auto Multi-Platform Versioning

---

## 1. Feature Overview

### 1.1 What We're Building
A comprehensive video editing system that:
1. Analyzes uploaded videos (transcription, scene detection, silence detection)
2. Automatically identifies best clips and hooks
3. Applies AI-powered edits (silence removal, jump cuts, dynamic zooms)
4. Optimizes for retention (pace, energy, engagement)
5. Generates multi-platform versions (TikTok, YouTube Shorts, Instagram, LinkedIn)

### 1.2 User Journey
1. User uploads a video (✅ Already implemented)
2. System processes video → extracts audio, creates proxy (✅ Already implemented)
3. **NEW:** System transcribes video and analyzes content
4. **NEW:** System proposes 3-5 candidate clips with retention scores
5. **NEW:** User selects a clip or uses "Auto-Edit" button
6. **NEW:** System applies edits (silence removal, jump cuts, captions, zooms)
7. **NEW:** System exports in multiple aspect ratios with platform-specific optimizations
8. User downloads final edited videos

---

## 2. Core Requirements

### 2.1 Must-Have Features (MVP)

#### 2.1.1 Transcription & Timeline Sync
**Priority:** P0 (Critical - Foundation for all other features)

**Requirements:**
- Auto speech-to-text transcription using Whisper (open-source, free)
- Map transcript words/phrases to precise timestamps
- Store transcript in database with word-level alignment
- Display transcript in UI with clickable timestamps (Descript-style)
- Allow manual transcript editing (for demo accuracy)

**Acceptance Criteria:**
- ✅ Transcript generated within 2x video duration (e.g., 60s video → 120s max)
- ✅ Word-level timestamp accuracy within 100ms
- ✅ Transcript accessible via API endpoint
- ✅ UI shows transcript with video player sync

**Technical Notes:**
- Use `faster-whisper` (faster than OpenAI Whisper, still free)
- Store transcript as JSON: `[{start, end, text, confidence}]`
- Cache transcripts to avoid re-processing

---

#### 2.1.2 Silence Detection & Scene Timestamps
**Priority:** P0 (Critical - Used by clip selection and editing)

**Requirements:**
- Detect silence segments (gaps > 0.6s)
- Detect scene changes (camera cuts)
- Generate segments.json with speech/silence/scene markers
- Store in database for quick retrieval

**Acceptance Criteria:**
- ✅ Silence detection accuracy > 90%
- ✅ Scene changes detected within 200ms of actual cut
- ✅ Segments available via API within 30s of upload

**Technical Notes:**
- Use `py-webrtcvad` or `pydub` for silence detection
- Use `PySceneDetect` for scene detection
- Run in background task after transcription

---

#### 2.1.3 Auto Clip Selection
**Priority:** P0 (Core value proposition)

**Requirements:**
- Analyze video and propose 3-5 candidate short clips (15-60s each)
- Score each clip by:
  - Speech density (words/second)
  - Audio energy (excited vs monotone)
  - Presence of keywords/hooks
  - Sentiment (positive/engaging)
- Display clips in UI with preview thumbnails and scores
- Allow user to select one or generate new candidates

**Acceptance Criteria:**
- ✅ At least 3 viable clips proposed for videos > 30s
- ✅ Clips are non-overlapping and diverse
- ✅ Each clip has a retention score (0-100)
- ✅ User can preview clips before editing

**Technical Notes:**
- Use heuristics first (fast, reliable)
- Optionally use LLM to re-rank top candidates
- Store candidates in database with metadata

---

#### 2.1.4 Basic AI Editing Pipeline
**Priority:** P0 (Core editing functionality)

**Requirements:**
- **Silence Removal:** Auto-remove detected silence segments
- **Jump Cuts:** Smooth cuts between speech segments (snap to word boundaries)
- **Dynamic Zooms:** Auto-zoom on key sentences (face tracking)
- **Auto Subtitles:** Burn-in captions with styling
- **Audio Normalization:** Normalize audio levels

**Acceptance Criteria:**
- ✅ Edited video has no silence gaps > 0.3s
- ✅ Cuts are smooth (no audio pops, lip-sync maintained)
- ✅ Zooms are smooth and centered on subject
- ✅ Captions are readable and properly timed
- ✅ Audio is normalized to -16 LUFS (broadcast standard)

**Technical Notes:**
- Use ffmpeg for all video operations
- Use `mediapipe` or OpenCV for face detection
- Generate Edit Decision List (EDL) before rendering
- Render as background job (Celery task)

---

#### 2.1.5 Export in Different Aspect Ratios
**Priority:** P0 (Multi-platform USP)

**Requirements:**
- Export edited video in 3 formats:
  - **9:16** (TikTok/Reels/Shorts) - 1080x1920
  - **1:1** (Instagram feed) - 1080x1080
  - **16:9** (YouTube) - 1920x1080
- Auto-reframe using face/subject tracking
- Maintain safe zones for captions/UI

**Acceptance Criteria:**
- ✅ All 3 aspect ratios generated from single edit
- ✅ Subject remains centered in all formats
- ✅ No important content cropped out
- ✅ Captions repositioned for each format

**Technical Notes:**
- Use face detection to compute crop center
- Use ffmpeg `crop` and `scale` filters
- Generate all 3 exports in parallel (Celery tasks)

---

### 2.2 Core USP Features

#### 2.2.1 Retention Analyzer
**Priority:** P1 (USP #2 - Retention Optimization)

**Requirements:**
- Score each 1-2s segment by:
  - Pace (speaking rate)
  - Energy (audio RMS)
  - Speech density
  - Sentiment
  - Visual motion
- Identify retention drops (low-score segments)
- Provide recommendations:
  - "Cut from 00:12-00:18 (low engagement)"
  - "Move hook from 00:21 to opening"

**Acceptance Criteria:**
- ✅ Retention scores displayed as heatmap on timeline
- ✅ Recommendations shown as actionable suggestions
- ✅ Scores are normalized (0-100) for easy interpretation

**Technical Notes:**
- Start with heuristics (fast, no training data needed)
- Use `librosa` for audio features
- Use OpenCV for motion detection
- Store scores in database for UI rendering

---

#### 2.2.2 Pace Optimizer
**Priority:** P1 (USP #2 - Retention Optimization)

**Requirements:**
- Automatically apply:
  - Faster cuts to slow areas
  - Punch-in zoom on key sentences
  - Remove filler words ("um", "uh", "like")
  - Keep sentences dense (remove pauses)

**Acceptance Criteria:**
- ✅ Filler words removed without audio artifacts
- ✅ Slow sections sped up by 10-20% (natural-sounding)
- ✅ Key moments emphasized with zoom
- ✅ Overall pace increased by 15-30% while maintaining clarity

**Technical Notes:**
- Use transcript word-level timestamps for filler detection
- Use ffmpeg `atempo` for speed adjustment (pitch-preserving)
- Apply micro-fades (10-30ms) to avoid audio pops

---

#### 2.2.3 Auto Hook Creator & Video Summary
**Priority:** P1 (Engagement booster)

**Requirements:**
- LLM identifies most viral/engaging sentence from transcript
- Generate 3 hook options (straight, punchy, funny)
- Generate video description/summary for each clip
- Suggest placing best hook at video opening

**Acceptance Criteria:**
- ✅ 3 distinct hook options provided
- ✅ Hooks are grounded in actual transcript (no hallucination)
- ✅ Summary is 1-2 sentences, platform-appropriate

**Technical Notes:**
- Use free/open LLM (HuggingFace models) or paid API (OpenAI/Gemini) for demo
- Prompt engineering: include transcript + platform context
- Store hooks in database with scores

---

#### 2.2.4 Auto Multi-Platform Versioning
**Priority:** P1 (USP #3 - Multi-platform)

**Requirements:**
- Generate platform-specific versions:
  - **TikTok:** Fast-paced, loud captions, high energy
  - **YouTube Shorts:** Slower, cleaner, informational
  - **LinkedIn:** Professional, clean subtitles, slower pace
  - **Instagram Reels:** Balanced, trendy captions
- Rewrite captions per platform tone
- Adjust pacing per platform (TikTok fastest, LinkedIn slowest)

**Acceptance Criteria:**
- ✅ 4 platform versions generated from single edit
- ✅ Captions rewritten with platform-appropriate tone
- ✅ Pacing optimized per platform (measurable difference)
- ✅ All exports ready for download

**Technical Notes:**
- Use LLM to rewrite captions per platform
- Adjust playback speed per platform (ffmpeg `setpts`)
- Batch export as separate Celery tasks

---

## 3. Technical Architecture

### 3.1 Data Models

#### New Database Tables

```python
# Transcript Model
class Transcript(Base):
    video_id: str (FK)
    segments: JSON  # [{start, end, text, confidence, words: [{word, start, end}]}]
    language: str
    created_at: datetime

# Clip Candidate Model
class ClipCandidate(Base):
    video_id: str (FK)
    start_time: float
    end_time: float
    duration: float
    score: float  # Retention score 0-100
    features: JSON  # {speech_density, energy, sentiment, keywords}
    hook_text: str
    created_at: datetime

# Edit Job Model
class EditJob(Base):
    video_id: str (FK)
    clip_candidate_id: str (FK, nullable)
    edit_options: JSON  # {remove_silence, jump_cuts, dynamic_zoom, captions, etc.}
    status: str  # queued, processing, completed, failed
    output_paths: JSON  # {9:16: path, 1:1: path, 16:9: path}
    created_at: datetime
    completed_at: datetime

# Retention Analysis Model
class RetentionAnalysis(Base):
    video_id: str (FK)
    segment_scores: JSON  # [{start, end, score, features}]
    recommendations: JSON  # [{type, start, end, message}]
    created_at: datetime
```

### 3.2 API Endpoints

```
POST   /api/videos/{video_id}/transcribe          # Start transcription
GET    /api/videos/{video_id}/transcript          # Get transcript
PUT    /api/videos/{video_id}/transcript          # Edit transcript

POST   /api/videos/{video_id}/analyze             # Run retention analysis
GET    /api/videos/{video_id}/retention           # Get retention scores

GET    /api/videos/{video_id}/candidates          # Get clip candidates
POST   /api/videos/{video_id}/candidates          # Generate new candidates

POST   /api/videos/{video_id}/edit                # Create edit job
GET    /api/videos/{video_id}/edit/{job_id}       # Get edit status
GET    /api/videos/{video_id}/edit/{job_id}/download  # Download edited video
```

### 3.3 Background Tasks (Celery)

```python
# New tasks to add:
transcribe_video_task(video_id)              # Whisper transcription
detect_silence_scenes_task(video_id)         # Silence + scene detection
generate_clip_candidates_task(video_id)      # AI clip selection
analyze_retention_task(video_id)             # Retention scoring
create_edit_job_task(job_id)                 # Render edited video
export_multi_platform_task(job_id)          # Multi-format export
```

---

## 4. Implementation Plan

### 4.1 Phase 1: Foundation (Day 1 - Morning)
**Goal:** Get transcription working end-to-end

**Tasks:**
1. ✅ Install dependencies: `faster-whisper`, `py-webrtcvad`, `PySceneDetect`
2. ✅ Create `Transcript` model and migration
3. ✅ Implement `transcribe_video_task` Celery task
4. ✅ Create transcription API endpoint
5. ✅ Test with sample video

**Deliverable:** Video transcription working, transcript stored in DB

---

### 4.2 Phase 2: Analysis (Day 1 - Afternoon)
**Goal:** Generate clip candidates and retention scores

**Tasks:**
1. ✅ Implement silence detection task
2. ✅ Implement scene detection task
3. ✅ Create `ClipCandidate` and `RetentionAnalysis` models
4. ✅ Implement heuristic-based clip selection
5. ✅ Implement basic retention scoring
6. ✅ Create API endpoints for candidates and retention

**Deliverable:** System proposes 3-5 clips with scores

---

### 4.3 Phase 3: Basic Editing (Day 2 - Morning)
**Goal:** Core editing pipeline working

**Tasks:**
1. ✅ Create `EditJob` model
2. ✅ Implement silence removal (ffmpeg)
3. ✅ Implement jump cuts with word-boundary snapping
4. ✅ Implement basic caption generation (burn-in)
5. ✅ Implement audio normalization
6. ✅ Create edit job API endpoint

**Deliverable:** Can generate edited video with silence removed + captions

---

### 4.4 Phase 4: Advanced Features (Day 2 - Afternoon)
**Goal:** Add zooms, pace optimization, multi-platform export

**Tasks:**
1. ✅ Implement face detection and dynamic zoom
2. ✅ Implement filler word removal
3. ✅ Implement pace optimization (speed adjustments)
4. ✅ Implement multi-aspect-ratio export
5. ✅ Test end-to-end flow

**Deliverable:** Full editing pipeline with all features

---

### 4.5 Phase 5: AI Enhancement (Day 2 - Evening)
**Goal:** Add LLM-powered features (hooks, captions, retention)

**Tasks:**
1. ✅ Integrate LLM API (HuggingFace or OpenAI)
2. ✅ Implement hook generation
3. ✅ Implement caption rewriting per platform
4. ✅ Enhance retention analysis with LLM insights
5. ✅ Polish UI/UX

**Deliverable:** AI-powered editing with multi-platform versioning

---

### 4.6 Phase 6: Frontend Integration (Day 3 - Morning)
**Goal:** Complete UI for editing feature

**Tasks:**
1. ✅ Create transcript viewer component (clickable, sync with video)
2. ✅ Create clip candidate selector UI
3. ✅ Create retention heatmap on timeline
4. ✅ Create edit options panel
5. ✅ Create export/download UI
6. ✅ Add loading states and progress indicators

**Deliverable:** Full-featured editing UI

---

## 5. Technology Stack Decisions

### 5.1 Transcription
- **Choice:** `faster-whisper` (open-source, free)
- **Why:** Faster than OpenAI Whisper, no API costs, runs locally
- **Fallback:** OpenAI Whisper API (if faster-whisper fails)

### 5.2 LLM for Hooks/Captions
- **Primary:** HuggingFace free models (e.g., `mistral-7b-instruct`)
- **Fallback:** OpenAI GPT-3.5-turbo (if free tier available)
- **Cost:** Target $0 for hackathon (use free tiers)

### 5.3 Video Processing
- **Choice:** FFmpeg (already in use)
- **Why:** Industry standard, handles all operations

### 5.4 Face Detection
- **Choice:** `mediapipe` (Google, free, fast)
- **Why:** Real-time capable, good accuracy, no GPU required

### 5.5 Audio Analysis
- **Choice:** `librosa` (open-source)
- **Why:** Comprehensive audio feature extraction

---

## 6. Success Metrics

### 6.1 Technical Metrics
- ✅ Transcription accuracy > 90% (WER)
- ✅ Clip selection: At least 3 viable clips for 80% of videos
- ✅ Edit processing time < 2x video duration
- ✅ Export success rate > 95%

### 6.2 User Experience Metrics
- ✅ Time from upload to first clip candidate < 3 minutes (for 60s video)
- ✅ Edit job completion < 5 minutes (for 30s clip)
- ✅ UI responsiveness: All interactions < 200ms

### 6.3 Demo Metrics
- ✅ Can demo end-to-end flow in < 5 minutes
- ✅ Clear before/after comparison visible
- ✅ Multi-platform exports ready for download

---

## 7. Risks & Mitigations

### 7.1 Risk: Transcription too slow
**Mitigation:** Use `faster-whisper` with GPU if available, or cache transcripts

### 7.2 Risk: LLM API costs
**Mitigation:** Use free HuggingFace models, limit API calls to demo videos only

### 7.3 Risk: Face detection fails (no faces in video)
**Mitigation:** Fallback to center crop or rule-of-thirds

### 7.4 Risk: Edit quality not good enough
**Mitigation:** Start with conservative edits, allow user to adjust parameters

### 7.5 Risk: Processing time too long
**Mitigation:** Optimize ffmpeg settings, use parallel processing for exports

---

## 8. Open Questions

1. **LLM Choice:** Should we use free HuggingFace models or pay for OpenAI/Gemini for better quality?
   - **Recommendation:** Start with HuggingFace, upgrade if needed

2. **GPU Availability:** Do we have GPU access for faster-whisper?
   - **Recommendation:** Test CPU first, GPU is nice-to-have

3. **Storage:** How to handle large edited video files?
   - **Recommendation:** Keep for 24 hours, then archive/delete

4. **User Authentication:** Do we need user accounts for hackathon?
   - **Recommendation:** Skip for MVP, use session-based tracking

---

## 9. Next Steps

1. **Review this PRD** with team
2. **Set up development environment** (install new dependencies)
3. **Start Phase 1** (transcription)
4. **Daily standup** to track progress
5. **Demo preparation** (Day 3 afternoon)

---

## 10. Appendix: File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── upload.py (existing)
│   │   └── edit.py (NEW - editing endpoints)
│   ├── models/
│   │   ├── video.py (existing)
│   │   ├── transcript.py (NEW)
│   │   ├── clip_candidate.py (NEW)
│   │   └── edit_job.py (NEW)
│   ├── services/
│   │   ├── video_processor.py (existing)
│   │   ├── transcription_service.py (NEW)
│   │   ├── clip_selector.py (NEW)
│   │   ├── retention_analyzer.py (NEW)
│   │   ├── editor.py (NEW)
│   │   └── llm_service.py (NEW)
│   └── workers/
│       └── tasks.py (extend with new tasks)

frontend/
├── src/
│   ├── pages/
│   │   └── VideoEdit.jsx (NEW - editing interface)
│   ├── components/
│   │   ├── edit/
│   │   │   ├── TranscriptViewer.jsx (NEW)
│   │   │   ├── ClipSelector.jsx (NEW)
│   │   │   ├── RetentionHeatmap.jsx (NEW)
│   │   │   └── EditOptions.jsx (NEW)
│   │   └── video/ (existing)
```

---

**Document Version:** 1.0  
**Last Updated:** Hackathon Day 1  
**Owner:** Development Team  
**Status:** Ready for Implementation

