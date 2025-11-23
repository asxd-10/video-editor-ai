from sqlalchemy import (
    Column, String, Integer, Float, Boolean, JSON, BigInteger,
    Enum as SQLEnum, ForeignKey, Index, Text, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
import enum
import uuid

class VideoStatus(str, enum.Enum):
    UPLOADING = "uploading"           # Upload in progress
    UPLOAD_COMPLETE = "upload_complete"  # File received, not processed
    VALIDATING = "validating"         # Checking file integrity
    EXTRACTING = "extracting"         # Creating proxy/thumbnails
    PROCESSING = "processing"         # Additional processing
    READY = "ready"                   # Ready to view
    FAILED = "failed"                 # Processing failed
    ARCHIVED = "archived"             # Soft delete

class VideoQuality(str, enum.Enum):
    ORIGINAL = "original"
    PROXY_720P = "proxy_720p"
    THUMBNAIL = "thumbnail"

class Video(Base):
    __tablename__ = "videos"
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)  # User's original name
    file_extension = Column(String(10), nullable=False)
    mime_type = Column(String(50))
    file_size = Column(Integer, nullable=False)  # bytes
    checksum_md5 = Column(String(32))  # File integrity
    
    # Storage paths (relative to storage root)
    original_path = Column(String(500), nullable=False)
    
    # Status and metadata
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.UPLOADING, nullable=False)
    error_message = Column(Text)  # If status = FAILED
    
    # Video technical metadata (null until extracted)
    duration_seconds = Column(Float)
    fps = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    bitrate_kbps = Column(Integer)
    has_audio = Column(Boolean, default=True)
    aspect_ratio = Column(String(10))  # e.g., "16:9", "9:16"
    
    # Processing metadata
    upload_started_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    upload_completed_at = Column(String)
    processing_started_at = Column(String)
    processing_completed_at = Column(String)
    
    # User metadata (for future multi-user support)
    uploaded_by = Column(String(50))  # User ID or session ID
    title = Column(String(255))  # User-provided title
    description = Column(Text)
    
    # Analysis metadata (temporary storage for silence/scene detection)
    # Note: Can't use 'metadata' - it's reserved by SQLAlchemy
    analysis_metadata = Column(JSON)  # {silence_segments: [...], scene_timestamps: [...]}
    
    # Soft delete
    deleted_at = Column(String)
    
    # Timestamps
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat(), nullable=False)
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), 
                       onupdate=lambda: datetime.utcnow().isoformat(), nullable=False)
    
    # Relationships - COMMENTED OUT: All models now use Media table, not Video
    # These relationships cannot work because foreign keys now point to media.video_id
    # assets = relationship("VideoAsset", back_populates="video", cascade="all, delete-orphan")
    # upload_chunks = relationship("UploadChunk", back_populates="video", cascade="all, delete-orphan")
    # processing_logs = relationship("ProcessingLog", back_populates="video", cascade="all, delete-orphan")
    # transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    # clip_candidates = relationship("ClipCandidate", back_populates="video", cascade="all, delete-orphan")
    # edit_jobs = relationship("EditJob", back_populates="video", cascade="all, delete-orphan")
    # ai_edit_jobs = relationship("AIEditJob", back_populates="video", cascade="all, delete-orphan")
    # retention_analysis = relationship("RetentionAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
    
    # Video Editing Relationships
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    clip_candidates = relationship("ClipCandidate", back_populates="video", cascade="all, delete-orphan")
    edit_jobs = relationship("EditJob", back_populates="video", cascade="all, delete-orphan")
    retention_analysis = relationship("RetentionAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_video_status', 'status'),
        Index('idx_video_created_at', 'created_at'),
        Index('idx_video_uploaded_by', 'uploaded_by'),
    )

class VideoAsset(Base):
    """Different versions/derivatives of the video (proxy, thumbnails, etc.)"""
    __tablename__ = "video_assets"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False)
    
    asset_type = Column(SQLEnum(VideoQuality), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    
    # Asset-specific metadata
    width = Column(Integer)
    height = Column(Integer)
    duration_seconds = Column(Float)
    
    # Processing info
    status = Column(String(20), default="pending")  # pending, processing, ready, failed
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="assets")
    
    __table_args__ = (
        Index('idx_asset_video_type', 'video_id', 'asset_type'),
    )

class UploadChunk(Base):
    """Track chunked uploads for resumability"""
    __tablename__ = "upload_chunks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False)
    
    chunk_number = Column(Integer, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    checksum = Column(String(32))  # MD5 of chunk
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="upload_chunks")
    
    __table_args__ = (
        Index('idx_chunk_video', 'video_id', 'chunk_number'),
    )

class ProcessingLog(Base):
    """Audit trail for all processing steps"""
    __tablename__ = "processing_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False)
    frame_id = Column(BigInteger, ForeignKey('frames.id'), nullable=True)  # Optional reference to frames table
    
    level = Column(String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR' (matches unified schema)
    step = Column(String(50))  # Processing step name (optional in unified schema)
    message = Column(Text, nullable=False)
    error_details = Column(JSON)  # JSONB in database, JSON in SQLAlchemy
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="processing_logs")
    
    __table_args__ = (
        Index('idx_log_video_step', 'video_id', 'step'),
    )