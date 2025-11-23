"""
AI Edit Job Model
Tracks AI-driven storytelling edit jobs
"""
from sqlalchemy import Column, String, JSON, ForeignKey, Enum as SQLEnum, Text, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
import uuid
import enum

class AIEditJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AIEditJob(Base):
    __tablename__ = "ai_edit_jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, index=True)  # References media.video_id (primary/legacy)
    video_ids = Column(JSON, nullable=True)  # List of video IDs for multi-video edits [video_id1, video_id2, ...]
    
    # Input data
    summary = Column(JSON, nullable=True)  # Video summary/description
    story_prompt = Column(JSON, nullable=False)  # User's story requirements
    
    # LLM-generated plan
    llm_plan = Column(JSON, nullable=True)  # Full LLM response (EDL, story_analysis, etc.)
    
    # Status tracking
    status = Column(SQLEnum(AIEditJobStatus), default=AIEditJobStatus.QUEUED)
    error_message = Column(Text)
    
    # Metadata
    compression_metadata = Column(JSON, nullable=True)  # Data compression stats
    validation_errors = Column(JSON, nullable=True)  # Validation warnings/errors
    llm_usage = Column(JSON, nullable=True)  # Token usage from LLM
    
    # Output paths (after applying edit)
    output_paths = Column(JSON, nullable=True)  # {aspect_ratio: path}
    
    # Timestamps (TIMESTAMPTZ in database)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    media = relationship("Media", back_populates="ai_edit_jobs")

