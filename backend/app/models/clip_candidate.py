from sqlalchemy import Column, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False)
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    
    # Scoring
    score = Column(Float, nullable=False)  # 0-100 retention score
    features = Column(JSON)  # {speech_density, energy, sentiment, keywords}
    
    # Hook
    hook_text = Column(String(500))
    hook_timestamp = Column(Float)
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="clip_candidates")

