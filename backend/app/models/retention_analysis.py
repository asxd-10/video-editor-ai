from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class RetentionAnalysis(Base):
    __tablename__ = "retention_analyses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False, unique=True)
    
    # Segment scores: [{start, end, score, features: {...}}]
    segment_scores = Column(JSON, nullable=False)
    
    # Recommendations: [{type, start, end, message, priority}]
    recommendations = Column(JSON, default=list)
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="retention_analysis")

