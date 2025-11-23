from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.media import Media  # Use Media instead of Video
from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.models.edit_job import EditJob, EditJobStatus
from app.services.clip_selector import ClipSelector
from app.workers.tasks import transcribe_video_task, analyze_video_task, create_edit_job_task
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/{video_id}/transcribe")
async def start_transcription(video_id: str, db: Session = Depends(get_db)):
    """Start transcription for a video"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
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
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if already analyzed
    if media.analysis_metadata:
        return {
            "status": "already_complete",
            "message": "Analysis already complete",
            "silence_segments": len(media.analysis_metadata.get("silence_segments", [])),
            "scene_timestamps": len(media.analysis_metadata.get("scene_timestamps", []))
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
    """Get clip candidates for a video (returns empty list if transcript doesn't exist)"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if transcript exists - if not, return empty list (don't error)
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    if not transcript:
        return {
            "video_id": video_id,
            "count": 0,
            "candidates": [],
            "message": "Transcript not found. Transcribe video first to generate candidates."
        }
    
    # Get existing candidates (don't auto-generate on GET - user must explicitly request)
    candidates = db.query(ClipCandidate).filter(
        ClipCandidate.video_id == video_id
    ).order_by(ClipCandidate.score.desc()).all()
    
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
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
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

# Pydantic models for edit job requests
class EditOptions(BaseModel):
    remove_silence: bool = True
    jump_cuts: bool = True
    dynamic_zoom: bool = False
    captions: bool = True
    caption_style: str = "burn_in"  # "burn_in" or "srt"
    pace_optimize: bool = False
    aspect_ratios: List[str] = ["16:9"]  # ["9:16", "1:1", "16:9"]

class CreateEditJobRequest(BaseModel):
    clip_candidate_id: Optional[str] = None
    edit_options: EditOptions = EditOptions()

@router.post("/{video_id}/edit")
async def create_edit_job(
    video_id: str,
    request: CreateEditJobRequest,
    db: Session = Depends(get_db)
):
    """Create a new edit job for a video"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Validate clip candidate if provided
    if request.clip_candidate_id:
        clip = db.query(ClipCandidate).filter(
            ClipCandidate.id == request.clip_candidate_id,
            ClipCandidate.video_id == video_id
        ).first()
        if not clip:
            raise HTTPException(status_code=404, detail="Clip candidate not found")
    
    # Create edit job
    edit_job = EditJob(
        video_id=video_id,
        clip_candidate_id=request.clip_candidate_id,
        edit_options=request.edit_options.dict(),
        status=EditJobStatus.QUEUED
    )
    db.add(edit_job)
    db.commit()
    db.refresh(edit_job)
    
    # Queue processing task
    task = create_edit_job_task.delay(edit_job.id)
    logger.info(f"Edit job {edit_job.id} queued, task_id: {task.id}")
    
    return {
        "job_id": edit_job.id,
        "status": edit_job.status,
        "task_id": task.id,
        "message": "Edit job created and queued"
    }

@router.get("/{video_id}/edit/{job_id}")
async def get_edit_job_status(
    video_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status of an edit job"""
    edit_job = db.query(EditJob).filter(
        EditJob.id == job_id,
        EditJob.video_id == video_id
    ).first()
    
    if not edit_job:
        raise HTTPException(status_code=404, detail="Edit job not found")
    
    # Convert output_paths to full URLs
    output_paths_urls = {}
    if edit_job.output_paths:
        from app.config import get_settings
        settings = get_settings()
        from pathlib import Path
        
        for aspect_ratio, path in edit_job.output_paths.items():
            if path:
                # If already a URL path (starts with /storage), use as is
                if path.startswith('/storage/'):
                    output_paths_urls[aspect_ratio] = path
                else:
                    # Convert relative or absolute path to URL
                    path_obj = Path(path)
                    try:
                        # Try to get relative path from BASE_STORAGE_PATH
                        relative_path = path_obj.relative_to(settings.BASE_STORAGE_PATH)
                        output_paths_urls[aspect_ratio] = f"/storage/{relative_path.as_posix()}"
                    except ValueError:
                        # If not relative, try to resolve it
                        if path_obj.is_absolute():
                            # Try to find if it's under BASE_STORAGE_PATH
                            try:
                                relative_path = path_obj.relative_to(settings.BASE_STORAGE_PATH)
                                output_paths_urls[aspect_ratio] = f"/storage/{relative_path.as_posix()}"
                            except ValueError:
                                # Fallback: use the path as is (might be a full URL or external path)
                                output_paths_urls[aspect_ratio] = path
                        else:
                            # Relative path - assume it's relative to BASE_STORAGE_PATH
                            output_paths_urls[aspect_ratio] = f"/storage/{path.lstrip('/')}"
    
    return {
        "job_id": edit_job.id,
        "video_id": edit_job.video_id,
        "clip_candidate_id": edit_job.clip_candidate_id,
        "status": edit_job.status,
        "edit_options": edit_job.edit_options,
        "output_paths": output_paths_urls,  # Return URLs instead of file paths
        "error_message": edit_job.error_message,
        "created_at": edit_job.created_at,
        "started_at": edit_job.started_at,
        "completed_at": edit_job.completed_at
    }

@router.get("/{video_id}/edit/{job_id}/download")
async def download_edited_video(
    video_id: str,
    job_id: str,
    aspect_ratio: str = "16:9",
    db: Session = Depends(get_db)
):
    """Download edited video for a specific aspect ratio"""
    edit_job = db.query(EditJob).filter(
        EditJob.id == job_id,
        EditJob.video_id == video_id
    ).first()
    
    if not edit_job:
        raise HTTPException(status_code=404, detail="Edit job not found")
    
    if edit_job.status != EditJobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Edit job not completed. Current status: {edit_job.status}"
        )
    
    if not edit_job.output_paths or aspect_ratio not in edit_job.output_paths:
        raise HTTPException(
            status_code=404,
            detail=f"Output for aspect ratio {aspect_ratio} not found"
        )
    
    output_path = edit_job.output_paths[aspect_ratio]
    
    # Check if file exists
    from pathlib import Path
    if not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=f"edited_{aspect_ratio.replace(':', '_')}.mp4"
    )

@router.get("/{video_id}/edit")
async def list_edit_jobs(
    video_id: str,
    db: Session = Depends(get_db)
):
    """List all edit jobs for a video"""
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Video not found")
    
    edit_jobs = db.query(EditJob).filter(
        EditJob.video_id == video_id
    ).order_by(EditJob.created_at.desc()).all()
    
    return {
        "video_id": video_id,
        "count": len(edit_jobs),
        "jobs": [
            {
                "job_id": job.id,
                "clip_candidate_id": job.clip_candidate_id,
                "status": job.status,
                "edit_options": job.edit_options,
                "output_paths": job.output_paths,
                "created_at": job.created_at,
                "completed_at": job.completed_at
            }
            for job in edit_jobs
        ]
    }

