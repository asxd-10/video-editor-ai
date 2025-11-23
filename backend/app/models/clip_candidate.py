from sqlalchemy import Column, String, Float, JSON, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
import uuid

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL in database
    video_id = Column(String, ForeignKey('media.video_id'), nullable=False)
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    
    # Scoring
    score = Column(Float, nullable=False)  # 0-100 retention score
    features = Column(JSON)  # {speech_density, energy, sentiment, keywords}
    
    # Hook
    hook_text = Column(String(500))
    hook_timestamp = Column(Float)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # TIMESTAMPTZ in database
    
    # Legacy Video relationship removed - use media relationship
    media = relationship("Media", back_populates="clip_candidates")

