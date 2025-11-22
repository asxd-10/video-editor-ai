# Video Editing Feature - Implementation Plan

## Quick Start Guide

This document provides step-by-step implementation instructions for the video editing feature. Follow phases in order.

---

## Prerequisites Check

Before starting, ensure you have:
- ✅ Video upload working (already done)
- ✅ Redis running (`redis-server`)
- ✅ Celery worker running
- ✅ FFmpeg installed and working
- ✅ Python 3.12+ with venv activated

---

## Phase 1: Setup & Dependencies (30 minutes)

### Step 1.1: Install New Python Dependencies

Add to `backend/requirements.txt`:

```txt
# Transcription
faster-whisper==1.0.3  # Faster Whisper implementation
torch==2.1.0  # Required by faster-whisper (CPU version)

# Audio Analysis
librosa==0.10.1
soundfile==0.12.1
py-webrtcvad==2.0.10  # Voice Activity Detection
pydub==0.25.1  # Audio manipulation

# Scene Detection
scenedetect[opencv]==0.6.2  # PySceneDetect

# Face Detection
mediapipe==0.10.8

# LLM (choose one)
# Option A: Free HuggingFace
transformers==4.36.0
torch==2.1.0
# Option B: OpenAI (if you have API key)
openai==1.6.1
```

**Install:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note:** For faster-whisper, if you have GPU:
```bash
pip install faster-whisper[gpu]
```

### Step 1.2: Verify Installations

Test in Python shell:
```python
from faster_whisper import WhisperModel
import librosa
import cv2
import mediapipe as mp
print("✅ All dependencies installed")
```

---

## Phase 2: Database Models (45 minutes)

### Step 2.1: Create Transcript Model

Create `backend/app/models/transcript.py`:

```python
from sqlalchemy import Column, String, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False, unique=True)
    
    # Transcript data: [{start, end, text, confidence, words: [...]}]
    segments = Column(JSON, nullable=False)
    language = Column(String(10), default="en")
    confidence = Column(JSON)  # Overall confidence metrics
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="transcript")
```

### Step 2.2: Create ClipCandidate Model

Create `backend/app/models/clip_candidate.py`:

```python
from sqlalchemy import Column, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    
    # Scoring
    score = Column(Float, nullable=False)  # 0-100 retention score
    features = Column(JSON)  # {speech_density, energy, sentiment, keywords}
    
    # Hook
    hook_text = Column(String(500))
    hook_timestamp = Column(Float)
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="clip_candidates")
```

### Step 2.3: Create EditJob Model

Create `backend/app/models/edit_job.py`:

```python
from sqlalchemy import Column, String, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid
import enum

class EditJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class EditJob(Base):
    __tablename__ = "edit_jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    clip_candidate_id = Column(String(36), ForeignKey('clip_candidates.id'), nullable=True)
    
    # Edit options
    edit_options = Column(JSON, nullable=False)  # {
    #   remove_silence: bool,
    #   jump_cuts: bool,
    #   dynamic_zoom: bool,
    #   captions: bool,
    #   caption_style: str,
    #   pace_optimize: bool,
    #   aspect_ratios: [str]  # ["9:16", "1:1", "16:9"]
    # }
    
    status = Column(SQLEnum(EditJobStatus), default=EditJobStatus.QUEUED)
    error_message = Column(String(500))
    
    # Output paths: {aspect_ratio: path}
    output_paths = Column(JSON)
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    started_at = Column(String)
    completed_at = Column(String)
    
    video = relationship("Video", back_populates="edit_jobs")
    clip_candidate = relationship("ClipCandidate")
```

### Step 2.4: Create RetentionAnalysis Model

Create `backend/app/models/retention_analysis.py`:

```python
from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class RetentionAnalysis(Base):
    __tablename__ = "retention_analyses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False, unique=True)
    
    # Segment scores: [{start, end, score, features: {...}}]
    segment_scores = Column(JSON, nullable=False)
    
    # Recommendations: [{type, start, end, message, priority}]
    recommendations = Column(JSON, default=list)
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="retention_analysis")
```

### Step 2.5: Update Video Model

Update `backend/app/models/video.py`:

Add relationships:
```python
# Add to Video class
transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
clip_candidates = relationship("ClipCandidate", back_populates="video", cascade="all, delete-orphan")
edit_jobs = relationship("EditJob", back_populates="video", cascade="all, delete-orphan")
retention_analysis = relationship("RetentionAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
```

### Step 2.6: Create Database Migration

```bash
cd backend
alembic revision --autogenerate -m "Add editing feature models"
alembic upgrade head
```

**Or manually create tables:**
```python
# In Python shell or migration script
from app.database import engine, Base
from app.models import transcript, clip_candidate, edit_job, retention_analysis
Base.metadata.create_all(bind=engine)
```

---

## Phase 3: Transcription Service (2 hours)

### Step 3.1: Create Transcription Service

Create `backend/app/services/transcription_service.py`:

```python
from faster_whisper import WhisperModel
from app.database import SessionLocal
from app.models.video import Video
from app.models.transcript import Transcript
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class TranscriptionService:
    def __init__(self):
        # Use "base" model for speed, "small" for better accuracy
        # Options: tiny, base, small, medium, large
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
    
    def transcribe_video(self, video_id: str) -> dict:
        """
        Transcribe video and save to database.
        Returns: {segments: [...], language: str}
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            # Check if transcript exists
            existing = db.query(Transcript).filter(Transcript.video_id == video_id).first()
            if existing:
                logger.info(f"Transcript already exists for {video_id}")
                return {
                    "segments": existing.segments,
                    "language": existing.language
                }
            
            # Extract audio if needed (or use existing audio track)
            audio_path = self._extract_audio(video.original_path, video_id)
            
            # Transcribe
            logger.info(f"Transcribing {video_id}...")
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                word_timestamps=True,
                language="en"  # Auto-detect if None
            )
            
            # Convert to list format
            transcript_segments = []
            for segment in segments:
                words = []
                for word in segment.words:
                    words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })
                
                transcript_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob,
                    "words": words
                })
            
            # Save to database
            transcript = Transcript(
                video_id=video_id,
                segments=transcript_segments,
                language=info.language,
                confidence={"avg_logprob": info.avg_logprob}
            )
            db.add(transcript)
            db.commit()
            
            logger.info(f"Transcription complete for {video_id}: {len(transcript_segments)} segments")
            
            return {
                "segments": transcript_segments,
                "language": info.language
            }
            
        except Exception as e:
            logger.error(f"Transcription failed for {video_id}: {e}")
            raise
        finally:
            db.close()
    
    def _extract_audio(self, video_path: str, video_id: str) -> str:
        """Extract audio to WAV file for transcription"""
        import ffmpeg
        from pathlib import Path
        
        output_dir = settings.TEMP_DIR / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / "audio.wav"
        
        if audio_path.exists():
            return str(audio_path)
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(str(audio_path), acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return str(audio_path)
        except ffmpeg.Error as e:
            raise Exception(f"Audio extraction failed: {e.stderr.decode()}")
```

### Step 3.2: Create Celery Task

Add to `backend/app/workers/tasks.py`:

```python
from app.services.transcription_service import TranscriptionService

@celery_app.task(bind=True, max_retries=3)
def transcribe_video_task(self, video_id: str):
    """Transcribe video using Whisper"""
    try:
        service = TranscriptionService()
        result = service.transcribe_video(video_id)
        logger.info(f"Transcription task completed for {video_id}")
        return result
    except Exception as e:
        logger.error(f"Transcription task failed: {e}")
        raise self.retry(exc=e, countdown=60)
```

### Step 3.3: Update Video Processing Task

Modify `process_video_task` in `backend/app/workers/tasks.py`:

Add after thumbnail generation:
```python
# Step 5: Transcribe video
log_processing_step(db, video_id, "transcribe", "started")
try:
    transcribe_video_task.delay(video_id)  # Async transcription
    log_processing_step(db, video_id, "transcribe", "started", "Transcription queued")
except Exception as e:
    log_processing_step(db, video_id, "transcribe", "failed", str(e))
    logger.warning(f"Transcription failed but continuing: {e}")
```

### Step 3.4: Create API Endpoint

Create `backend/app/api/edit.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.video import Video
from app.models.transcript import Transcript
from app.workers.tasks import transcribe_video_task

router = APIRouter()

@router.post("/{video_id}/transcribe")
async def start_transcription(video_id: str, db: Session = Depends(get_db)):
    """Start transcription for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Check if already transcribed
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if transcript:
        return {"status": "already_complete", "transcript_id": transcript.id}
    
    # Queue transcription
    transcribe_video_task.delay(video_id)
    return {"status": "queued", "message": "Transcription started"}

@router.get("/{video_id}/transcript")
async def get_transcript(video_id: str, db: Session = Depends(get_db)):
    """Get transcript for a video"""
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(404, "Transcript not found")
    
    return {
        "video_id": video_id,
        "segments": transcript.segments,
        "language": transcript.language,
        "created_at": transcript.created_at
    }
```

### Step 3.5: Register Router

Update `backend/app/main.py`:

```python
from app.api import upload, edit

app.include_router(upload.router, prefix="/api/videos", tags=["videos"])
app.include_router(edit.router, prefix="/api/videos", tags=["editing"])
```

### Step 3.6: Test Transcription

```bash
# Start backend
uvicorn app.main:app --reload

# In another terminal, test API
curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe
curl http://localhost:8000/api/videos/{video_id}/transcript
```

---

## Phase 4: Silence & Scene Detection (1.5 hours)

### Step 4.1: Create Detection Service

Create `backend/app/services/analysis_service.py`:

```python
import ffmpeg
import numpy as np
from pydub import AudioSegment
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from app.config import get_settings

settings = get_settings()

class AnalysisService:
    def detect_silence(self, audio_path: str, min_silence_len: int = 600) -> list:
        """
        Detect silence segments in audio.
        Returns: [(start_ms, end_ms), ...]
        """
        audio = AudioSegment.from_wav(audio_path)
        
        # Detect silence (threshold in dB, min_silence_len in ms)
        silence_segments = []
        chunks = audio[::100]  # Check every 100ms
        
        in_silence = False
        silence_start = None
        
        for i, chunk in enumerate(chunks):
            if chunk.dBFS < -40:  # Silence threshold
                if not in_silence:
                    in_silence = True
                    silence_start = i * 100
            else:
                if in_silence:
                    silence_duration = (i * 100) - silence_start
                    if silence_duration >= min_silence_len:
                        silence_segments.append((silence_start / 1000.0, (i * 100) / 1000.0))
                    in_silence = False
        
        return silence_segments
    
    def detect_scenes(self, video_path: str, threshold: float = 30.0) -> list:
        """
        Detect scene changes in video.
        Returns: [timestamp_seconds, ...]
        """
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        
        video_manager.set_duration()
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        
        scene_list = scene_manager.get_scene_list()
        timestamps = [scene[0].get_seconds() for scene in scene_list]
        
        return timestamps
```

### Step 4.2: Add Celery Task

Add to `backend/app/workers/tasks.py`:

```python
from app.services.analysis_service import AnalysisService

@celery_app.task
def analyze_video_task(video_id: str):
    """Detect silence and scenes"""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        
        service = AnalysisService()
        
        # Extract audio
        audio_path = settings.TEMP_DIR / video_id / "audio.wav"
        if not audio_path.exists():
            # Extract audio first
            # ... (use transcription service method)
            pass
        
        # Detect silence
        silence_segments = service.detect_silence(str(audio_path))
        
        # Detect scenes
        scene_timestamps = service.detect_scenes(video.original_path)
        
        # Store in video analysis_metadata or separate table
        # For now, store in Video model as JSON
        video.analysis_metadata = {
            "silence_segments": silence_segments,
            "scene_timestamps": scene_timestamps
        }
        db.commit()
        
        return {
            "silence_segments": silence_segments,
            "scene_timestamps": scene_timestamps
        }
    finally:
        db.close()
```

---

## Phase 5: Clip Selection (2 hours)

### Step 5.1: Create Clip Selector Service

Create `backend/app/services/clip_selector.py`:

```python
from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.services.analysis_service import AnalysisService
import numpy as np

class ClipSelector:
    def __init__(self):
        self.analysis_service = AnalysisService()
    
    def generate_candidates(self, video_id: str, db, min_duration: float = 15.0, max_duration: float = 60.0) -> list:
        """
        Generate clip candidates with retention scores.
        Returns: List of ClipCandidate objects
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        
        if not transcript:
            raise ValueError("Transcript not found. Transcribe video first.")
        
        # Get silence segments
        silence_segments = video.analysis_metadata.get("silence_segments", []) if video.analysis_metadata else []
        
        # Generate candidates using heuristics
        candidates = []
        
        # Strategy 1: High speech density segments
        candidates.extend(self._find_high_density_segments(transcript, min_duration, max_duration))
        
        # Strategy 2: Segments with keywords/hooks
        candidates.extend(self._find_keyword_segments(transcript, min_duration, max_duration))
        
        # Strategy 3: Segments around scene changes
        scene_timestamps = video.analysis_metadata.get("scene_timestamps", []) if video.analysis_metadata else []
        candidates.extend(self._find_scene_based_segments(scene_timestamps, video.duration_seconds, min_duration, max_duration))
        
        # Score and rank candidates
        scored_candidates = []
        for candidate in candidates:
            score = self._calculate_retention_score(candidate, transcript, silence_segments)
            scored_candidates.append({
                **candidate,
                "score": score
            })
        
        # Sort by score and take top 5
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = scored_candidates[:5]
        
        # Save to database
        clip_objects = []
        for cand in top_candidates:
            clip = ClipCandidate(
                video_id=video_id,
                start_time=cand["start"],
                end_time=cand["end"],
                duration=cand["end"] - cand["start"],
                score=cand["score"],
                features=cand.get("features", {}),
                hook_text=cand.get("hook_text"),
                hook_timestamp=cand.get("hook_timestamp")
            )
            db.add(clip)
            clip_objects.append(clip)
        
        db.commit()
        return clip_objects
    
    def _find_high_density_segments(self, transcript, min_duration, max_duration):
        """Find segments with high speech density"""
        candidates = []
        
        for segment in transcript.segments:
            duration = segment["end"] - segment["start"]
            if min_duration <= duration <= max_duration:
                word_count = len(segment.get("words", []))
                speech_density = word_count / duration if duration > 0 else 0
                
                if speech_density > 2.0:  # > 2 words per second
                    candidates.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "features": {"speech_density": speech_density, "word_count": word_count}
                    })
        
        return candidates
    
    def _find_keyword_segments(self, transcript, min_duration, max_duration):
        """Find segments with engaging keywords"""
        keywords = ["amazing", "incredible", "watch", "check", "here", "now", "you", "this", "that"]
        candidates = []
        
        for segment in transcript.segments:
            text_lower = segment["text"].lower()
            keyword_count = sum(1 for kw in keywords if kw in text_lower)
            
            if keyword_count > 0:
                duration = segment["end"] - segment["start"]
                if min_duration <= duration <= max_duration:
                    candidates.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "features": {"keyword_count": keyword_count},
                        "hook_text": segment["text"][:100]  # First 100 chars
                    })
        
        return candidates
    
    def _find_scene_based_segments(self, scene_timestamps, video_duration, min_duration, max_duration):
        """Find segments around scene changes"""
        candidates = []
        
        for i, scene_time in enumerate(scene_timestamps):
            if i + 1 < len(scene_timestamps):
                start = scene_time
                end = scene_timestamps[i + 1]
                duration = end - start
                
                if min_duration <= duration <= max_duration:
                    candidates.append({
                        "start": start,
                        "end": end,
                        "features": {"scene_based": True}
                    })
        
        return candidates
    
    def _calculate_retention_score(self, candidate, transcript, silence_segments):
        """Calculate retention score (0-100)"""
        score = 50  # Base score
        
        # Speech density bonus
        speech_density = candidate.get("features", {}).get("speech_density", 0)
        score += min(speech_density * 10, 20)  # Max +20
        
        # Keyword bonus
        keyword_count = candidate.get("features", {}).get("keyword_count", 0)
        score += min(keyword_count * 5, 15)  # Max +15
        
        # Silence penalty
        start, end = candidate["start"], candidate["end"]
        silence_in_segment = sum(
            max(0, min(silence_end, end) - max(silence_start, start))
            for silence_start, silence_end in silence_segments
        )
        silence_ratio = silence_in_segment / (end - start) if (end - start) > 0 else 0
        score -= silence_ratio * 30  # Penalty up to -30
        
        # Duration bonus (prefer 20-40s)
        duration = end - start
        if 20 <= duration <= 40:
            score += 10
        elif duration < 15 or duration > 60:
            score -= 10
        
        return max(0, min(100, score))
```

### Step 5.2: Add API Endpoint

Add to `backend/app/api/edit.py`:

```python
from app.services.clip_selector import ClipSelector

@router.get("/{video_id}/candidates")
async def get_clip_candidates(video_id: str, db: Session = Depends(get_db)):
    """Get clip candidates for a video"""
    candidates = db.query(ClipCandidate).filter(
        ClipCandidate.video_id == video_id
    ).order_by(ClipCandidate.score.desc()).all()
    
    if not candidates:
        # Generate candidates
        selector = ClipSelector()
        candidates = selector.generate_candidates(video_id, db)
    
    return {
        "video_id": video_id,
        "candidates": [
            {
                "id": c.id,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "duration": c.duration,
                "score": c.score,
                "hook_text": c.hook_text,
                "features": c.features
            }
            for c in candidates
        ]
    }

@router.post("/{video_id}/candidates")
async def generate_candidates(video_id: str, db: Session = Depends(get_db)):
    """Generate new clip candidates"""
    selector = ClipSelector()
    candidates = selector.generate_candidates(video_id, db)
    
    return {"status": "success", "count": len(candidates)}
```

---

## Phase 6: Basic Editing Pipeline (3 hours)

This is the core editing functionality. Due to length, I'll provide the structure and key functions.

### Step 6.1: Create Editor Service

Create `backend/app/services/editor.py`:

Key functions needed:
1. `remove_silence()` - Use transcript + silence segments to create EDL
2. `apply_jump_cuts()` - Cut at word boundaries
3. `add_captions()` - Generate SRT and burn-in with ffmpeg
4. `normalize_audio()` - Use ffmpeg loudnorm
5. `render_video()` - Combine all edits into final output

### Step 6.2: Create Edit Job Task

Add Celery task that:
1. Takes edit options
2. Applies all edits
3. Renders to specified aspect ratios
4. Saves output paths to EditJob model

---

## Next Steps

Continue with:
- Phase 7: Advanced Features (zooms, pace optimization)
- Phase 8: LLM Integration (hooks, caption rewriting)
- Phase 9: Frontend UI
- Phase 10: Testing & Polish

**For now, focus on Phases 1-5 to get foundation working!**

---

## Quick Reference: API Endpoints Summary

```
POST   /api/videos/{video_id}/transcribe     # Start transcription
GET    /api/videos/{video_id}/transcript     # Get transcript
GET    /api/videos/{video_id}/candidates     # Get clip candidates
POST   /api/videos/{video_id}/candidates     # Generate new candidates
POST   /api/videos/{video_id}/edit           # Create edit job
GET    /api/videos/{video_id}/edit/{job_id}  # Get edit status
```

---

**Status:** Ready for Phase 1 implementation  
**Estimated Time:** 8-10 hours for Phases 1-5  
**Next Review:** After Phase 5 completion

