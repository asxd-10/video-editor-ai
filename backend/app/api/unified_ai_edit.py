"""
Unified AI Edit Endpoint
Complete workflow: Generate AI edit -> Apply -> Upload to S3 -> Callback
Designed for external integrations (e.g., iMessage)
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl
from app.database import get_db
from app.models.ai_edit_job import AIEditJob, AIEditJobStatus
from app.models.edit_job import EditJob, EditJobStatus
from app.models.media import Media
from app.models.transcript import Transcript
from app.services.ai.data_loader import DataLoader
from app.services.ai.edl_converter import EDLConverter
from app.services.editor import EditorService
from app.services.storage import StorageService
from app.workers.tasks import generate_ai_edit_task, apply_ai_edit_task
from datetime import datetime
import logging
import httpx
import os
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()


# Request Models
class UnifiedAIEditRequest(BaseModel):
    """Unified request for complete AI edit workflow"""
    video_ids: List[str]  # List of video IDs to edit
    summary: Dict[str, Any]  # Summary JSON
    story_prompt: Dict[str, Any]  # Story prompt JSON
    aspect_ratios: Optional[List[str]] = ["16:9"]  # Output aspect ratios
    callback_url: Optional[HttpUrl] = None  # iMessage API callback URL
    callback_data: Optional[Dict[str, Any]] = None  # Additional data to send in callback


@router.post("/ai-edit/unified")
async def unified_ai_edit(
    request: UnifiedAIEditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Unified endpoint for complete AI edit workflow.
    
    Workflow:
    1. Generate AI edit plan
    2. Apply edit and render video
    3. Upload rendered video to S3 (Supabase storage)
    4. Callback iMessage API with public URL
    
    Args:
        request: UnifiedAIEditRequest with video_ids, summary, story_prompt, etc.
    
    Returns:
        {
            "job_id": str,
            "status": "queued",
            "message": "AI edit workflow started",
            "callback_url": str (if provided)
        }
    """
    if not request.video_ids or len(request.video_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one video_id is required")
    
    primary_video_id = request.video_ids[0]
    is_multi_video = len(request.video_ids) > 1
    
    # Validate videos exist
    for vid_id in request.video_ids:
        media = db.query(Media).filter(Media.video_id == vid_id).first()
        if not media:
            raise HTTPException(status_code=404, detail=f"Video {vid_id} not found")
    
    # Prepare summary and story_prompt
    summary = request.summary if isinstance(request.summary, dict) else {}
    story_prompt = request.story_prompt if isinstance(request.story_prompt, dict) else {}
    
    # Create AI edit job
    try:
        ai_edit_job = AIEditJob(
            video_id=primary_video_id,
            video_ids=request.video_ids if is_multi_video else None,
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
    
    # Queue background task for complete workflow
    # Import here to avoid circular imports
    from app.workers.tasks import unified_ai_edit_workflow_task
    task = unified_ai_edit_workflow_task.delay(
        str(ai_edit_job.id),
        request.aspect_ratios or ["16:9"],
        str(request.callback_url) if request.callback_url else None,
        request.callback_data or {}
    )
    
    logger.info(
        f"Unified AI edit workflow queued: Job {ai_edit_job.id}, "
        f"Task {task.id}, Videos: {len(request.video_ids)}, "
        f"Callback: {request.callback_url}"
    )
    
    return {
        "job_id": ai_edit_job.id,
        "task_id": task.id,
        "status": "queued",
        "message": "AI edit workflow started. Video will be processed and uploaded to S3.",
        "callback_url": str(request.callback_url) if request.callback_url else None,
        "video_ids": request.video_ids,
        "is_multi_video": is_multi_video
    }


@router.get("/ai-edit/unified/{job_id}")
async def get_unified_ai_edit_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get status of unified AI edit workflow.
    
    Returns:
        {
            "job_id": str,
            "status": str,
            "ai_edit_status": str,
            "render_status": str,
            "s3_url": str (if uploaded),
            "error": str (if failed)
        }
    """
    job = db.query(AIEditJob).filter(AIEditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="AI edit job not found")
    
    # Get latest edit job if exists
    edit_job = db.query(EditJob).filter(
        EditJob.edit_options.contains({"_ai_edit_job_id": job_id})
    ).order_by(EditJob.created_at.desc()).first()
    
    result = {
        "job_id": job.id,
        "status": "processing",
        "ai_edit_status": job.status,
        "render_status": None,
        "s3_url": None,
        "error": job.error_message
    }
    
    if edit_job:
        result["render_status"] = edit_job.status
        result["edit_job_id"] = edit_job.id
        
        # Check if output_paths contain S3 URLs
        if edit_job.output_paths:
            # Look for S3 URLs in output_paths
            for aspect_ratio, path in edit_job.output_paths.items():
                if isinstance(path, str) and ("supabase.co" in path or "s3" in path.lower()):
                    result["s3_url"] = path
                    result["aspect_ratio"] = aspect_ratio
                    break
    
    # Determine overall status
    if job.status == AIEditJobStatus.COMPLETED and edit_job and edit_job.status == EditJobStatus.COMPLETED:
        result["status"] = "completed"
    elif job.status == AIEditJobStatus.FAILED or (edit_job and edit_job.status == EditJobStatus.FAILED):
        result["status"] = "failed"
    elif job.status == AIEditJobStatus.PROCESSING or (edit_job and edit_job.status == EditJobStatus.PROCESSING):
        result["status"] = "processing"
    
    return result

