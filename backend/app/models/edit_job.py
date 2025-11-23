from sqlalchemy import Column, String, JSON, ForeignKey, Enum as SQLEnum, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False)
    clip_candidate_id = Column(BigInteger, ForeignKey('clip_candidates.id'), nullable=True)  # bigint in database
    
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
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    started_at = Column(DateTime(timezone=True), nullable=True)  # TIMESTAMPTZ in database
    completed_at = Column(DateTime(timezone=True), nullable=True)  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="edit_jobs")
    clip_candidate = relationship("ClipCandidate")

