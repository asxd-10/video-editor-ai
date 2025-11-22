from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.services.clip_selector import ClipSelector
from app.workers.tasks import transcribe_video_task, analyze_video_task
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/{video_id}/transcribe")
async def start_transcription(video_id: str, db: Session = Depends(get_db)):
    """Start transcription for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already transcribed
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if transcript:
        return {
            "status": "already_complete",
            "transcript_id": transcript.id,
            "message": "Transcript already exists"
        }
    
    # Queue transcription task
    task = transcribe_video_task.delay(video_id)
    logger.info(f"Transcription queued for {video_id}, task_id: {task.id}")
    
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Transcription started"
    }

@router.get("/{video_id}/transcript")
async def get_transcript(video_id: str, db: Session = Depends(get_db)):
    """Get transcript for a video"""
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found. Start transcription first.")
    
    return {
        "video_id": video_id,
        "transcript_id": transcript.id,
        "segments": transcript.segments,
        "language": transcript.language,
        "confidence": transcript.confidence,
        "created_at": transcript.created_at
    }

@router.get("/{video_id}/transcript/status")
async def get_transcript_status(video_id: str, db: Session = Depends(get_db)):
    """Check if transcript exists for a video"""
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    
    if transcript:
        return {
            "status": "complete",
            "transcript_id": transcript.id,
            "segment_count": len(transcript.segments),
            "language": transcript.language,
            "created_at": transcript.created_at
        }
    else:
        return {
            "status": "not_found",
            "message": "Transcript not found. Use POST /{video_id}/transcribe to start transcription."
        }

@router.post("/{video_id}/analyze")
async def start_analysis(video_id: str, db: Session = Depends(get_db)):
    """Start video analysis (silence + scene detection)"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already analyzed
    if video.analysis_metadata:
        return {
            "status": "already_complete",
            "message": "Analysis already complete",
            "silence_segments": len(video.analysis_metadata.get("silence_segments", [])),
            "scene_timestamps": len(video.analysis_metadata.get("scene_timestamps", []))
        }
    
    # Queue analysis task
    task = analyze_video_task.delay(video_id)
    logger.info(f"Analysis queued for {video_id}, task_id: {task.id}")
    
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Analysis started"
    }

@router.get("/{video_id}/candidates")
async def get_clip_candidates(video_id: str, db: Session = Depends(get_db)):
    """Get clip candidates for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if transcript exists
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(
            status_code=400, 
            detail="Transcript not found. Transcribe video first."
        )
    
    # Get existing candidates or generate new ones
    candidates = db.query(ClipCandidate).filter(
        ClipCandidate.video_id == video_id
    ).order_by(ClipCandidate.score.desc()).all()
    
    if not candidates:
        # Generate candidates
        selector = ClipSelector()
        candidates = selector.generate_candidates(video_id, db)
    
    return {
        "video_id": video_id,
        "count": len(candidates),
        "candidates": [
            {
                "id": c.id,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "duration": c.duration,
                "score": c.score,
                "hook_text": c.hook_text,
                "hook_timestamp": c.hook_timestamp,
                "features": c.features
            }
            for c in candidates
        ]
    }

@router.post("/{video_id}/candidates")
async def generate_candidates(video_id: str, db: Session = Depends(get_db)):
    """Generate new clip candidates"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if transcript exists
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        raise HTTPException(
            status_code=400, 
            detail="Transcript not found. Transcribe video first."
        )
    
    # Delete old candidates
    db.query(ClipCandidate).filter(ClipCandidate.video_id == video_id).delete()
    db.commit()
    
    # Generate new candidates
    selector = ClipSelector()
    candidates = selector.generate_candidates(video_id, db)
    
    return {
        "status": "success",
        "count": len(candidates),
        "message": f"Generated {len(candidates)} clip candidates"
    }

