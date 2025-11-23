"""
AI Edit API Endpoints
Handles AI-driven storytelling edit generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
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
    desired_length_percentage: Optional[float] = 50.0  # 25-100, percentage of original video length
    desired_length: Optional[str] = None  # DEPRECATED: Use desired_length_percentage instead (short=30%, medium=50%, long=85%)
    style_preferences: Optional[dict] = {
        "pacing": "moderate",
        "transitions": "smooth",
        "emphasis": "balanced"
    }

class FrameLevelData(BaseModel):
    """Frame-level data from the new format"""
    frame_timestamp: float
    description: str

class SceneData(BaseModel):
    """Scene data from scene_level_data"""
    description: str
    start: float
    end: float
    metadata: Optional[Dict[str, Any]] = {}
    scene_metadata: Optional[Dict[str, Any]] = {}

class SceneLevelData(BaseModel):
    """Scene-level data structure"""
    scene_count: int
    scenes: List[SceneData]

class TranscriptSegment(BaseModel):
    """Transcript segment from transcription_level_data"""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None

class TranscriptionLevelData(BaseModel):
    """Transcription-level data structure"""
    transcript_text: Optional[str] = None
    transcript_data: Optional[List[TranscriptSegment]] = None
    segment_count: Optional[int] = 0
    language_code: Optional[str] = None

class SummaryResult(BaseModel):
    """Single video result from summary.results array"""
    media_id: str  # This is the video ID (mapped to video_id internally)
    video_url: str
    frame_level_data: Optional[List[FrameLevelData]] = []
    scene_level_data: Optional[SceneLevelData] = None
    transcription_level_data: Optional[TranscriptionLevelData] = None
    
    class Config:
        # Allow extra fields that might be in the JSON
        extra = "allow"

class SummaryInput(BaseModel):
    """Summary input matching the new format"""
    success: Optional[bool] = True
    message_ids: Optional[List[str]] = []
    results: Optional[List[SummaryResult]] = []  # Array of video data
    
    class Config:
        # Allow extra fields that might be in the JSON
        extra = "allow"

class VideoDataInput(BaseModel):
    """Complete video data provided in request (no database needed) - LEGACY FORMAT"""
    video_id: str
    video_url: str  # Required: Video URL to download/process
    duration_seconds: Optional[float] = None
    frames: Optional[List[Dict[str, Any]]] = None  # Frame-level data
    scenes: Optional[List[Dict[str, Any]]] = None  # Scene-level data
    transcription: Optional[Dict[str, Any]] = None  # Transcription data
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata

class GenerateAIEditRequest(BaseModel):
    """Request model matching the new JSON format"""
    summary: Optional[SummaryInput] = None  # New format: Contains results array with video data
    story_prompt: Optional[StoryPromptInput] = None
    callback_url: Optional[str] = None
    callback_data: Optional[Dict[str, Any]] = None
    video_ids: Optional[List[str]] = None  # Optional: Message IDs or other identifiers
    auto_apply: Optional[bool] = True  # If True, automatically apply edit after generation (DEFAULT: True - pipeline runs automatically)
    aspect_ratios: Optional[List[str]] = ["16:9"]  # Aspect ratios for rendering (if auto_apply=True)
    
    # Legacy fields for backward compatibility
    videos_data: Optional[List[VideoDataInput]] = None  # DEPRECATED: Use summary.results instead
    
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"


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
    request: GenerateAIEditRequest
):
    """
    Generate AI-driven storytelling edit plan.
    
    SELF-SUFFICIENT: All data comes from POST request JSON, no database queries.
    
    Supports both single and multi-video edits:
    - Provide videos_data with complete video information (video_url, frames, scenes, transcription)
    - All processing uses provided data, no database lookups
    
    Args:
        video_id: Primary video ID (for job tracking, can be any identifier)
        request: Complete request with videos_data containing all video information
    """
    import json
    
    # Log the complete incoming request for debugging
    try:
        request_dict = request.dict()
        # Pretty print the JSON for readability
        request_json = json.dumps(request_dict, indent=2, default=str)
        logger.info("=" * 80)
        logger.info("INCOMING POST REQUEST - /api/videos/{video_id}/ai-edit/generate")
        logger.info("=" * 80)
        logger.info(f"Video ID (path): {video_id}")
        logger.info(f"Request JSON:\n{request_json}")
        logger.info("=" * 80)
        
        # Also print to console for immediate visibility
        print("\n" + "=" * 80)
        print("INCOMING POST REQUEST - /api/videos/{video_id}/ai-edit/generate")
        print("=" * 80)
        print(f"Video ID (path): {video_id}")
        print(f"Request JSON:\n{request_json}")
        print("=" * 80 + "\n")
    except Exception as e:
        logger.warning(f"Failed to log request JSON: {e}")
        # Fallback: log raw request object
        logger.info(f"Request object: {request}")
        print(f"Request object: {request}")
    # Extract videos from summary.results (NEW FORMAT) or fallback to videos_data (LEGACY)
    videos_data = []
    video_ids = []
    
    if request.summary and request.summary.results:
        # NEW FORMAT: Extract from summary.results
        for result in request.summary.results:
            vid_id = result.media_id  # media_id is the video ID
            video_url = result.video_url
            
            if not video_url:
                raise HTTPException(
                    status_code=400,
                    detail=f"video_url is required for media_id {vid_id}"
                )
            
            # Transform frame_level_data to frames format
            frames = []
            if result.frame_level_data:
                for frame_data in result.frame_level_data:
                    frames.append({
                        "frame_timestamp": frame_data.frame_timestamp,
                        "timestamp_seconds": frame_data.frame_timestamp,  # Add normalized field
                        "description": frame_data.description,
                        "llm_response": frame_data.description,  # Add normalized field
                        "status": "completed"  # Required by data compressor filter
                    })
            
            # Transform scene_level_data.scenes to scenes format
            scenes = []
            duration_from_scenes = 0.0
            if result.scene_level_data and result.scene_level_data.scenes:
                for scene_data in result.scene_level_data.scenes:
                    scenes.append({
                        "start": scene_data.start,
                        "end": scene_data.end,
                        "description": scene_data.description,
                        "metadata": scene_data.metadata or {},
                        "scene_metadata": scene_data.scene_metadata or {}
                    })
                    # Calculate duration from last scene end
                    if scene_data.end > duration_from_scenes:
                        duration_from_scenes = scene_data.end
            
            # Transform transcription_level_data to transcription format
            transcription = None
            if result.transcription_level_data:
                transcript_data = result.transcription_level_data.transcript_data
                if transcript_data is None:
                    transcript_data = []
                
                transcription = {
                    "transcript_text": result.transcription_level_data.transcript_text,
                    "transcript_data": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                            "speaker": seg.speaker if hasattr(seg, 'speaker') else None
                        }
                        for seg in transcript_data
                    ],
                    "segment_count": result.transcription_level_data.segment_count or len(transcript_data),
                    "language_code": result.transcription_level_data.language_code
                }
            
            # Build video data entry
            videos_data.append({
                "video_id": vid_id,
                "video_url": video_url,
                "duration_seconds": duration_from_scenes if duration_from_scenes > 0 else None,
                "frames": frames,
                "scenes": scenes,
                "transcription": transcription
            })
            video_ids.append(vid_id)
    
    elif request.videos_data and len(request.videos_data) > 0:
        # LEGACY FORMAT: Use videos_data
        videos_data = [v.dict() for v in request.videos_data]
        video_ids = [v["video_id"] for v in videos_data]
    else:
        raise HTTPException(
            status_code=400,
            detail="summary.results is required. Provide at least one video result with media_id, video_url, frame_level_data, scene_level_data, and transcription_level_data."
        )
    
    if not videos_data or len(videos_data) == 0:
        raise HTTPException(
            status_code=400,
            detail="No video data found. Provide summary.results with at least one video."
        )
    
    is_multi_video = len(videos_data) > 1
    
    # Process provided data (no database queries)
    from app.services.ai.data_loader import DataLoader
    
    # Extract data from provided videos_data
    all_frames = []
    all_scenes = []
    all_transcriptions = []
    videos_metadata = []
    total_duration = 0.0
    
    for vid_data in videos_data:
        vid_id = vid_data["video_id"]
        video_url = vid_data.get("video_url")
        if not video_url:
            raise HTTPException(
                status_code=400,
                detail=f"video_url is required for video {vid_id}"
            )
        
        # Calculate duration from scenes if not provided
        duration = vid_data.get("duration_seconds")
        if duration is None or duration == 0:
            scenes = vid_data.get("scenes", [])
            if scenes:
                # Get max end time from scenes
                duration = max([s.get("end", 0) for s in scenes], default=0.0)
            else:
                duration = 0.0
        
        total_duration += duration
        
        # Collect frames
        frames = vid_data.get("frames", [])
        for frame in frames:
            # Ensure frame has required fields for data compressor
            if "status" not in frame:
                frame["status"] = "completed"
            if "timestamp_seconds" not in frame and "frame_timestamp" in frame:
                frame["timestamp_seconds"] = frame["frame_timestamp"]
            if "llm_response" not in frame and "description" in frame:
                frame["llm_response"] = frame["description"]
            # Tag with source video for multi-video edits
            frame["source_video_id"] = vid_id
            frame["video_id"] = vid_id  # Also keep video_id for backward compatibility
            all_frames.append(frame)
        
        # Collect scenes
        scenes = vid_data.get("scenes", [])
        for scene in scenes:
            scene["video_id"] = vid_id  # Tag with source video
            all_scenes.append(scene)
        
        # Collect transcriptions
        transcription = vid_data.get("transcription")
        if transcription:
            transcription["video_id"] = vid_id  # Tag with source video
            all_transcriptions.append(transcription)
        
        # Build metadata
        videos_metadata.append({
            "video_id": vid_id,
            "video_url": video_url,
            "duration": duration,
            "frames_count": len(frames),
            "scenes_count": len(scenes),
            "has_transcription": transcription is not None
        })
    
    # Sort frames by timestamp to preserve order (critical for proper sequencing)
    all_frames.sort(key=lambda f: (f.get("source_video_id", ""), f.get("timestamp_seconds") or f.get("frame_timestamp", 0)))
    
    # Sort scenes by start time to preserve order (critical for proper sequencing)
    all_scenes.sort(key=lambda s: (s.get("source_video_id", ""), s.get("start", 0)))
    
    # Extract transcript segments from provided transcriptions
    data_loader = DataLoader(None)  # No DB needed
    transcript_segments = []
    for transcription in all_transcriptions:
        if transcription:
            segments = data_loader.extract_transcript_segments(transcription)
            # Tag segments with source video_id
            for seg in segments:
                seg["source_video_id"] = transcription.get("video_id")
            transcript_segments.extend(segments)
    
    # Prepare data structure (matching what DataLoader would return)
    data = {
        "frames": all_frames,
        "scenes": all_scenes,
        "transcription": all_transcriptions[0] if len(all_transcriptions) == 1 else all_transcriptions,
        "video_duration": total_duration,
        "videos": videos_metadata
    }
    
    # Log frame counts for debugging
    logger.info(f"Prepared data for pipeline: {len(all_frames)} frames, {len(all_scenes)} scenes, {len(transcript_segments)} transcript segments")
    if len(all_frames) > 0:
        sample_frame = all_frames[0]
        logger.info(f"Sample frame keys: {list(sample_frame.keys())}, has description: {bool(sample_frame.get('description'))}, has llm_response: {bool(sample_frame.get('llm_response'))}, has status: {bool(sample_frame.get('status'))}")
    
    # Prepare summary (handle new format vs legacy format)
    if request.summary:
        summary_dict = request.summary.dict()
        # New format has success, message_ids, results - extract useful info
        # For backward compatibility, create a summary structure
        summary = {
            "success": summary_dict.get("success", True),
            "message_ids": summary_dict.get("message_ids", []),
            "video_summary": "",  # Extract from results if needed
            "key_moments": [],
            "content_type": "presentation",
            "main_topics": [],
            "speaker_style": "casual",
            "results_count": len(summary_dict.get("results", []))
        }
    else:
        # Fallback to defaults
        summary = {
            "success": True,
            "message_ids": [],
        "video_summary": "",
        "key_moments": [],
        "content_type": "presentation",
        "main_topics": [],
            "speaker_style": "casual",
            "results_count": 0
    }
    
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
    
    # Create job ID (UUID, no database needed)
    import uuid
    job_id = str(uuid.uuid4())
    
    # Check if auto_apply is enabled
    if request.auto_apply:
        # Pipeline: Generate -> Apply -> Save to processed_dir
        from app.workers.tasks import generate_and_apply_ai_edit_pipeline
        aspect_ratios = request.aspect_ratios or ["16:9"]
        task = generate_and_apply_ai_edit_pipeline.delay(
            job_id=job_id,
            videos_data=videos_data,
            summary=summary,
            story_prompt=story_prompt,
            data=data,  # Pre-processed data
            transcript_segments=transcript_segments,
            videos_metadata=videos_metadata if is_multi_video else None,
            aspect_ratios=aspect_ratios,
            primary_video_id=video_id,  # For output directory
            callback_url=request.callback_url,
            callback_data=request.callback_data
        )
        
        logger.info(f"AI edit pipeline {job_id} queued (generate + apply + save), task_id: {task.id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "task_id": task.id,
            "message": "AI edit pipeline started (generate -> apply -> save to processed_dir)",
            "video_ids": video_ids,
            "is_multi_video": is_multi_video,
            "auto_apply": True,
            "aspect_ratios": aspect_ratios
        }
    else:
        # Just generate the plan
        from app.workers.tasks import generate_ai_edit_task_standalone
        task = generate_ai_edit_task_standalone.delay(
            job_id=job_id,
            videos_data=videos_data,
            summary=summary,
            story_prompt=story_prompt,
            data=data,  # Pre-processed data
            transcript_segments=transcript_segments,
            videos_metadata=videos_metadata if is_multi_video else None
        )
    
        logger.info(f"AI edit job {job_id} queued ({'multi-video' if is_multi_video else 'single-video'}), task_id: {task.id}")
    
    return {
            "job_id": job_id,
            "status": "queued",
        "task_id": task.id,
            "message": "AI edit generation started (no database dependencies)",
            "video_ids": video_ids,
            "is_multi_video": is_multi_video,
            "auto_apply": False
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
    
    # Determine if this is a multi-video edit
    video_ids = job.video_ids if job.video_ids and len(job.video_ids) > 0 else [job.video_id]
    is_multi_video = len(video_ids) > 1
    
    # Cache media data for all videos to avoid DB queries in Celery task (prevents timeout)
    if is_multi_video:
        # Multi-video: load data for all videos
        multi_video_data = {}
        for vid_id in video_ids:
            media = db.query(Media).filter(Media.video_id == vid_id).first()
            if not media:
                logger.warning(f"Media not found for video_id: {vid_id}, skipping")
                continue
            
            transcript_segments = None
            if edit_options.get("captions"):
                transcript = db.query(Transcript).filter(Transcript.video_id == vid_id).first()
                if transcript:
                    transcript_segments = transcript.segments
            
            multi_video_data[vid_id] = {
                "video_url": media.video_url,
                "original_path": media.original_path,
                "duration_seconds": media.duration_seconds or 0.0,
                "has_audio": getattr(media, 'has_audio', True) if hasattr(media, 'has_audio') else True,
                "transcript_segments": transcript_segments
            }
        
        if not multi_video_data:
            raise HTTPException(status_code=404, detail="No valid media found for video_ids")
        
        cached_media_data = None  # Not used for multi-video
    else:
        # Single video: use existing logic
        media = db.query(Media).filter(Media.video_id == video_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    transcript_segments = None
    if edit_options.get("captions"):
        transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        if transcript:
            transcript_segments = transcript.segments
    
    cached_media_data = {
        "video_url": media.video_url,
        "original_path": media.original_path,
        "duration_seconds": media.duration_seconds or 0.0,
        "has_audio": getattr(media, 'has_audio', True) if hasattr(media, 'has_audio') else True,
        "transcript_segments": transcript_segments
    }
    multi_video_data = None
    
    # Create EditJob record (will be processed by Celery)
    edit_job = EditJob(
        video_id=video_ids[0],  # Primary video_id for output directory
        clip_candidate_id=None,  # AI edit doesn't use clip candidates
        edit_options={
            **edit_options,
            "_ai_edl": editor_edl,  # Store EDL in edit_options for the task
            "_ai_edit_job_id": job.id,  # Link to AI edit job
            "_media_data": cached_media_data,  # Cache media data for single video
            "_multi_video_data": multi_video_data  # Cache media data for multi-video
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

