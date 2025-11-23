from sqlalchemy import Column, String, JSON, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
import uuid

class RetentionAnalysis(Base):
    __tablename__ = "retention_analysis"  # Use retention_analysis (singular) to match database
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False, unique=True)
    
    # Segment scores: [{start, end, score, features: {...}}]
    segment_scores = Column(JSON, nullable=False)
    
    # Recommendations: [{type, start, end, message, priority}]
    recommendations = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="retention_analysis")

