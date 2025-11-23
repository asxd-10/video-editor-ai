"""
AI Edit API Endpoints
Handles AI-driven storytelling edit generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.ai_edit_job import AIEditJob, AIEditJobStatus
from app.models.edit_job import EditJob, EditJobStatus
from app.models.media import Media
from app.models.transcript import Transcript
from app.services.ai.data_loader import DataLoader
from app.services.ai.storytelling_agent import StorytellingAgent
from app.services.ai.edl_converter import EDLConverter
from app.services.editor import EditorService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models
class StoryPromptInput(BaseModel):
    target_audience: Optional[str] = "general"
    story_arc: Optional[dict] = {
        "hook": "Grab attention in first 3 seconds",
        "build": "Build interest and context",
        "climax": "Main point/revelation",
        "resolution": "Conclusion/call-to-action"
    }
    tone: Optional[str] = "educational"  # educational, entertaining, dramatic, inspirational
    key_message: Optional[str] = ""
    desired_length: Optional[str] = "medium"  # short, medium, long
    style_preferences: Optional[dict] = {
        "pacing": "moderate",
        "transitions": "smooth",
        "emphasis": "balanced"
    }

class SummaryInput(BaseModel):
    video_summary: Optional[str] = ""
    key_moments: Optional[list] = []
    content_type: Optional[str] = "presentation"
    main_topics: Optional[list] = []
    speaker_style: Optional[str] = "casual"

class GenerateAIEditRequest(BaseModel):
    summary: Optional[SummaryInput] = None
    story_prompt: Optional[StoryPromptInput] = None  # Allow None for testing


@router.get("/{video_id}/ai-edit/data")
async def get_ai_edit_data(video_id: str, db: Session = Depends(get_db)):
    """
    Load all data needed for AI editing (media, transcription, frames, scenes).
    
    Note: video_id here refers to the video_id field in the media table,
    not the videos table. This is for AI editing use case.
    """
    # Load data from Supabase tables (media table is source of truth)
    data_loader = DataLoader(db)
    try:
        data = data_loader.load_all_data(video_id)
    except ValueError as e:
        db.rollback()  # Rollback on error
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"Error loading data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")
    
    # Extract transcript segments
    transcription = data.get("transcription")
    transcript_segments = data_loader.extract_transcript_segments(transcription) if transcription else []
    
    # Get media record for video URL
    from app.models.media import Media
    media_record = db.query(Media).filter(Media.video_id == video_id).first()
    media_dict = data.get("media", {})
    if media_record:
        # Ensure video_url and original_path are included
        media_dict["video_url"] = media_record.video_url
        media_dict["original_path"] = media_record.original_path
    
    return {
        "video_id": video_id,
        "media": media_dict,
        "transcription": {
            "status": transcription.get("status") if transcription else None,
            "segment_count": len(transcript_segments),
            "has_data": bool(transcript_segments)
        },
        "frames": {
            "count": len(data.get("frames", [])),
            "has_data": len(data.get("frames", [])) > 0
        },
        "scenes": {
            "count": len(data.get("scenes", [])),
            "has_data": len(data.get("scenes", [])) > 0
        },
        "video_duration": data.get("video_duration", 0.0)
    }


@router.post("/{video_id}/ai-edit/generate")
async def generate_ai_edit(
    video_id: str,
    request: GenerateAIEditRequest,
    db: Session = Depends(get_db)
):
    """
    Generate AI-driven storytelling edit plan.
    
    Note: video_id here refers to the video_id field in the media table,
    not the videos table. This is for AI editing use case.
    """
    # Load data (media table is source of truth)
    data_loader = DataLoader(db)
    try:
        data = data_loader.load_all_data(video_id)
    except ValueError as e:
        db.rollback()  # Rollback any failed transaction
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()  # Rollback on any error
        logger.error(f"Error loading data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")
    
    # Extract transcript segments
    transcription = data.get("transcription")
    transcript_segments = data_loader.extract_transcript_segments(transcription) if transcription else []
    
    # Prepare summary (handle missing/partial data)
    summary = request.summary.dict() if request.summary else {}
    # Merge with defaults for missing fields
    default_summary = {
        "video_summary": "",
        "key_moments": [],
        "content_type": "presentation",
        "main_topics": [],
        "speaker_style": "casual"
    }
    summary = {**default_summary, **summary}  # User values override defaults
    
    # Prepare story prompt (handle missing/partial data)
    story_prompt = request.story_prompt.dict() if request.story_prompt else {}
    # Merge with defaults for missing fields
    default_story_prompt = {
        "target_audience": "general",
        "story_arc": {
            "hook": "Grab attention in first 3 seconds",
            "build": "Build interest and context",
            "climax": "Main point/revelation",
            "resolution": "Conclusion/call-to-action"
        },
        "tone": "educational",
        "key_message": "",
        "desired_length": "medium",
        "style_preferences": {
            "pacing": "moderate",
            "transitions": "smooth",
            "emphasis": "balanced"
        }
    }
    # Deep merge for nested dicts
    if "story_arc" in story_prompt:
        story_prompt["story_arc"] = {**default_story_prompt["story_arc"], **story_prompt["story_arc"]}
    if "style_preferences" in story_prompt:
        story_prompt["style_preferences"] = {**default_story_prompt["style_preferences"], **story_prompt["style_preferences"]}
    story_prompt = {**default_story_prompt, **story_prompt}  # User values override defaults
    
    # Create AI edit job
    try:
        ai_edit_job = AIEditJob(
            video_id=video_id,
            summary=summary,
            story_prompt=story_prompt,
            status=AIEditJobStatus.QUEUED
        )
        db.add(ai_edit_job)
        db.commit()
        db.refresh(ai_edit_job)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating AI edit job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create edit job: {str(e)}")
    
    # Queue background task
    from app.workers.tasks import generate_ai_edit_task
    task = generate_ai_edit_task.delay(ai_edit_job.id)
    
    logger.info(f"AI edit job {ai_edit_job.id} queued, task_id: {task.id}")
    
    return {
        "job_id": ai_edit_job.id,
        "status": ai_edit_job.status,
        "task_id": task.id,
        "message": "AI edit generation started"
    }


@router.get("/{video_id}/ai-edit/plan/{job_id}")
async def get_ai_edit_plan(
    video_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get generated AI edit plan.
    """
    job = db.query(AIEditJob).filter(
        AIEditJob.id == job_id,
        AIEditJob.video_id == video_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="AI edit job not found")
    
    return {
        "job_id": job.id,
        "status": job.status,
        "summary": job.summary,
        "story_prompt": job.story_prompt,
        "llm_plan": job.llm_plan,
        "compression_metadata": job.compression_metadata,
        "validation_errors": job.validation_errors,
        "llm_usage": job.llm_usage,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


class ApplyAIEditRequest(BaseModel):
    aspect_ratios: list = ["16:9"]

@router.post("/{video_id}/ai-edit/apply/{job_id}")
async def apply_ai_edit(
    video_id: str,
    job_id: str,
    request: ApplyAIEditRequest = ApplyAIEditRequest(),
    db: Session = Depends(get_db)
):
    """
    Apply AI edit plan to video (render final output).
    """
    job = db.query(AIEditJob).filter(
        AIEditJob.id == job_id,
        AIEditJob.video_id == video_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="AI edit job not found")
    
    if job.status != AIEditJobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"AI edit job not completed (status: {job.status})"
        )
    
    if not job.llm_plan:
        raise HTTPException(status_code=400, detail="No edit plan available")
    
    # Convert LLM EDL to EditorService format
    converter = EDLConverter()
    editor_edl = converter.convert_llm_edl_to_editor_format(
        job.llm_plan.get("edl", [])
    )
    
    # Validate EDL is not empty
    if not editor_edl or len(editor_edl) == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid segments in edit plan. EDL is empty after conversion."
        )
    
    # Create edit options
    edit_options = converter.create_edit_options_from_plan(job.llm_plan)
    if request.aspect_ratios:
        edit_options["aspect_ratios"] = request.aspect_ratios
    
    # Cache media data to avoid DB queries in Celery task (prevents timeout)
    media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Get transcript segments if captions are enabled
    transcript_segments = None
    if edit_options.get("captions"):
        transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        if transcript:
            transcript_segments = transcript.segments
    
    # Cache media data
    cached_media_data = {
        "video_url": media.video_url,
        "original_path": media.original_path,
        "duration_seconds": media.duration_seconds or 0.0,
        "has_audio": getattr(media, 'has_audio', True) if hasattr(media, 'has_audio') else True,
        "transcript_segments": transcript_segments
    }
    
    # Create EditJob record (will be processed by Celery)
    edit_job = EditJob(
        video_id=video_id,
        clip_candidate_id=None,  # AI edit doesn't use clip candidates
        edit_options={
            **edit_options,
            "_ai_edl": editor_edl,  # Store EDL in edit_options for the task
            "_ai_edit_job_id": job.id,  # Link to AI edit job
            "_media_data": cached_media_data  # Cache media data to avoid DB query in task
        },
        status=EditJobStatus.QUEUED
    )
    db.add(edit_job)
    db.commit()
    db.refresh(edit_job)
    
    # Queue background rendering task (non-blocking)
    from app.workers.tasks import apply_ai_edit_task
    task = apply_ai_edit_task.delay(str(edit_job.id))
    logger.info(f"AI edit rendering queued: EditJob {edit_job.id}, Celery task {task.id}")
    
    return {
        "job_id": job.id,
        "edit_job_id": edit_job.id,
        "status": "queued",
        "message": "Edit rendering started in background. Poll /api/videos/{video_id}/edit/{edit_job_id} for status.",
        "poll_url": f"/api/videos/{video_id}/edit/{edit_job.id}"
    }


@router.get("/{video_id}/ai-edit")
async def list_ai_edit_jobs(video_id: str, db: Session = Depends(get_db)):
    """
    List all AI edit jobs for a video.
    """
    jobs = db.query(AIEditJob).filter(
        AIEditJob.video_id == video_id
    ).order_by(AIEditJob.created_at.desc()).all()
    
    return {
        "video_id": video_id,
        "jobs": [
            {
                "id": job.id,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "has_plan": bool(job.llm_plan),
                "has_output": bool(job.output_paths)
            }
            for job in jobs
        ]
    }

