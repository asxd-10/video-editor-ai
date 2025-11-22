from sqlalchemy import Column, String, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey('videos.id'), nullable=False, unique=True)
    
    # Transcript data: [{start, end, text, confidence, words: [...]}]
    segments = Column(JSON, nullable=False)
    language = Column(String(10), default="en")
    confidence = Column(JSON)  # Overall confidence metrics
    
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    video = relationship("Video", back_populates="transcript")

