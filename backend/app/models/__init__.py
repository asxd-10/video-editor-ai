"""
Database models for the video editor application.
Unified schema with Media as core table.
"""
# Unified Media Model (primary)
from app.models.media import Media, MediaStatus, MediaType

# Legacy Video Model (kept for backward compatibility during migration)
from app.models.video import (
    Video,
    VideoStatus,
    VideoQuality,
    VideoAsset,
    UploadChunk,
    ProcessingLog
)

# Current models
from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.models.edit_job import EditJob, EditJobStatus
from app.models.retention_analysis import RetentionAnalysis
from app.models.ai_edit_job import AIEditJob, AIEditJobStatus

# Aidit models (frame processing, scene indexing, transcription)
from app.models.aidit_models import (
    VideoProcessing,
    Frame,
    SceneIndex,
    Transcription
)

__all__ = [
    # Unified Media (primary)
    "Media",
    "MediaStatus",
    "MediaType",
    # Legacy Video (deprecated - use Media)
    "Video",
    "VideoStatus",
    "VideoQuality",
    # Shared models
    "VideoAsset",
    "UploadChunk",
    "ProcessingLog",
    "Transcript",
    "ClipCandidate",
    "EditJob",
    "EditJobStatus",
    "RetentionAnalysis",
    "AIEditJob",
    "AIEditJobStatus",
    # Aidit models
    "VideoProcessing",
    "Frame",
    "SceneIndex",
    "Transcription",
]

