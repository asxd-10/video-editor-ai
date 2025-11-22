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

