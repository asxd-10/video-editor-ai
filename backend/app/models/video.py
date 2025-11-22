from sqlalchemy import (
    Column, String, Integer, Float, Boolean, JSON, 
    Enum as SQLEnum, ForeignKey, Index, Text
)
from sqlalchemy.orm import relationship
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
    
    # Soft delete
    deleted_at = Column(String)
    
    # Timestamps
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat(), nullable=False)
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), 
                       onupdate=lambda: datetime.utcnow().isoformat(), nullable=False)
    
    # Relationships
    assets = relationship("VideoAsset", back_populates="video", cascade="all, delete-orphan")
    upload_chunks = relationship("UploadChunk", back_populates="video", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="video", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_video_status', 'status'),
        Index('idx_video_created_at', 'created_at'),
        Index('idx_video_uploaded_by', 'uploaded_by'),
    )

class VideoAsset(Base):
    """Different versions/derivatives of the video (proxy, thumbnails, etc.)"""
    __tablename__ = "video_assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    
    asset_type = Column(SQLEnum(VideoQuality), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    
    # Asset-specific metadata
    width = Column(Integer)
    height = Column(Integer)
    duration_seconds = Column(Float)
    
    # Processing info
    status = Column(String(20), default="pending")  # pending, processing, ready, failed
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="assets")
    
    __table_args__ = (
        Index('idx_asset_video_type', 'video_id', 'asset_type'),
    )

class UploadChunk(Base):
    """Track chunked uploads for resumability"""
    __tablename__ = "upload_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    
    chunk_number = Column(Integer, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    checksum = Column(String(32))  # MD5 of chunk
    uploaded_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="upload_chunks")
    
    __table_args__ = (
        Index('idx_chunk_video', 'video_id', 'chunk_number'),
    )

class ProcessingLog(Base):
    """Audit trail for all processing steps"""
    __tablename__ = "processing_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    
    step = Column(String(50), nullable=False)  # e.g., "extract_metadata", "create_proxy"
    status = Column(String(20), nullable=False)  # started, completed, failed
    message = Column(Text)
    error_details = Column(JSON)  # Stack trace if failed
    
    started_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    completed_at = Column(String)
    duration_seconds = Column(Float)
    
    video = relationship("Video", back_populates="processing_logs")
    
    __table_args__ = (
        Index('idx_log_video_step', 'video_id', 'step'),
    )