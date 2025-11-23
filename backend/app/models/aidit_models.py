"""
Aidit Models - Frame processing, scene indexing, and transcription
These models align with the unified schema
"""
from sqlalchemy import (
    Column, String, Integer, Float, BigInteger, Text, JSON, 
    ForeignKey, Index, UniqueConstraint, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime

class VideoProcessing(Base):
    """Frame processing status and configuration"""
    __tablename__ = "video_processing"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, unique=True, index=True)
    
    status = Column(String(50), nullable=False, default='pending', index=True)
    processing_type = Column(String(50))  # 'frame_indexing', 'scene_indexing', 'transcription', 'analysis'
    granularity_seconds = Column(Float)
    prompt = Column(Text)
    model = Column(String(100))  # LLM model name
    
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    failed_frames = Column(Integer, default=0)
    
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    media = relationship("Media", back_populates="video_processing")
    
    __table_args__ = (
        Index('idx_video_processing_video_id', 'video_id'),
        Index('idx_video_processing_status', 'status'),
    )


class Frame(Base):
    """Frame-level data with LLM responses"""
    __tablename__ = "frames"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, index=True)
    
    frame_number = Column(Integer, nullable=False)
    timestamp_seconds = Column(Float, nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default='pending')
    llm_response = Column(Text)  # LLM-generated description
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    media = relationship("Media", back_populates="frames")
    
    __table_args__ = (
        UniqueConstraint('video_id', 'frame_number', name='uq_frames_video_frame'),
        Index('idx_frames_video_id', 'video_id'),
        Index('idx_frames_frame_number', 'frame_number'),
        Index('idx_frames_timestamp', 'timestamp_seconds'),
    )


class SceneIndex(Base):
    """Scene extraction results"""
    __tablename__ = "scene_indexes"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, index=True)
    
    video_db_id = Column(String)  # videodb ID
    index_id = Column(String, nullable=False)
    extraction_type = Column(String(50), default='shot_based')
    prompt = Column(Text)
    
    status = Column(String(50), nullable=False, default='pending', index=True)
    scene_count = Column(Integer, default=0)
    scenes_data = Column(JSON)  # JSONB in PostgreSQL, JSON in SQLAlchemy
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    media = relationship("Media", back_populates="scene_indexes")
    
    __table_args__ = (
        UniqueConstraint('video_id', 'index_id', name='uq_scene_indexes_video_index'),
        Index('idx_scene_indexes_video_id', 'video_id'),
        Index('idx_scene_indexes_index_id', 'index_id'),
        Index('idx_scene_indexes_status', 'status'),
    )


class Transcription(Base):
    """Unified transcription data (from both codebases)"""
    __tablename__ = "transcriptions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, unique=True, index=True)
    
    video_db_id = Column(String)  # videodb ID (aidit)
    language_code = Column(String(10))
    status = Column(String(50), nullable=False, default='pending', index=True)
    
    transcript_data = Column(JSON)  # Full segment data (JSONB in PostgreSQL)
    transcript_text = Column(Text)  # Plain text version
    segment_count = Column(Integer, default=0)
    
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    media = relationship("Media", back_populates="transcription")
    
    __table_args__ = (
        Index('idx_transcriptions_video_id', 'video_id'),
        Index('idx_transcriptions_status', 'status'),
    )

