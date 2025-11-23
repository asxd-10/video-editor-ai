"""
Unified Media Model
Replaces both Video (current) and media (aidit) tables
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, JSON, 
    Enum as SQLEnum, ForeignKey, Index, Text, BigInteger
)
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum
import uuid

class MediaStatus(str, enum.Enum):
    """Media processing status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOAD_COMPLETE = "upload_complete"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"

class MediaType(str, enum.Enum):
    """Media type"""
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"

class Media(Base):
    """
    Unified media table - replaces both 'videos' and aidit 'media' tables
    Supports both file uploads and URL-based media
    """
    __tablename__ = "media"
    
    # Primary key (BIGSERIAL in SQL, BigInteger in SQLAlchemy)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Unique identifier (TEXT) - UUID from current or custom from aidit
    video_id = Column(String, nullable=False, unique=True, index=True)
    
    # URL/Path (supports both file paths and URLs)
    video_url = Column(Text)  # URL (aidit) or null (current file-based)
    original_path = Column(Text)  # File path (current) or URL (aidit)
    
    # Media type
    media_type = Column(String(20), nullable=False, default=MediaType.VIDEO.value)
    
    # File metadata (from current videos table)
    filename = Column(String(255))
    original_filename = Column(String(255))
    file_extension = Column(String(10))
    mime_type = Column(String(50))
    file_size = Column(BigInteger)  # bytes
    checksum_md5 = Column(String(32))
    
    # Technical metadata
    duration_seconds = Column(Float)
    fps = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    bitrate_kbps = Column(Integer)
    has_audio = Column(Boolean, default=True)
    aspect_ratio = Column(String(10))  # e.g., "16:9", "9:16"
    
    # Status and error handling
    status = Column(String(50), nullable=False, default=MediaStatus.PENDING.value, index=True)
    error_message = Column(Text)
    
    # User metadata
    uploaded_by = Column(String(50), index=True)
    title = Column(Text)
    description = Column(Text)
    
    # Processing timestamps
    upload_started_at = Column(String)
    upload_completed_at = Column(String)
    processing_started_at = Column(String)
    processing_completed_at = Column(String)
    
    # Analysis metadata (temporary storage for silence/scene detection)
    analysis_metadata = Column(JSON)  # {silence_segments: [...], scene_timestamps: [...]}
    
    # Soft delete
    deleted_at = Column(String)
    
    # Timestamps (using String for ISO format compatibility)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat(), index=True)
    updated_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat(),
                       onupdate=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    assets = relationship("VideoAsset", back_populates="media", cascade="all, delete-orphan")
    upload_chunks = relationship("UploadChunk", back_populates="media", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="media", cascade="all, delete-orphan")
    
    # Video Editing Relationships
    transcript = relationship("Transcript", back_populates="media", uselist=False, cascade="all, delete-orphan")
    transcription = relationship("Transcription", back_populates="media", uselist=False, cascade="all, delete-orphan")
    clip_candidates = relationship("ClipCandidate", back_populates="media", cascade="all, delete-orphan")
    edit_jobs = relationship("EditJob", back_populates="media", cascade="all, delete-orphan")
    ai_edit_jobs = relationship("AIEditJob", back_populates="media", cascade="all, delete-orphan")
    retention_analysis = relationship("RetentionAnalysis", back_populates="media", uselist=False, cascade="all, delete-orphan")
    
    # Aidit relationships
    video_processing = relationship("VideoProcessing", back_populates="media", cascade="all, delete-orphan")
    frames = relationship("Frame", back_populates="media", cascade="all, delete-orphan")
    scene_indexes = relationship("SceneIndex", back_populates="media", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_media_status', 'status'),
        Index('idx_media_created_at', 'created_at'),
        Index('idx_media_uploaded_by', 'uploaded_by'),
        Index('idx_media_deleted_at', 'deleted_at'),
    )
    
    def __repr__(self):
        return f"<Media(id={self.id}, video_id={self.video_id}, status={self.status})>"

