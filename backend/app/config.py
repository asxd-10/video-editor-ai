from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Video Upload Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    ALLOWED_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: list = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    ALLOWED_MIME_TYPES: list = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
    
    # Storage
    BASE_STORAGE_PATH: Path = Path("../storage")
    UPLOAD_DIR: Path = BASE_STORAGE_PATH / "uploads"
    PROCESSED_DIR: Path = BASE_STORAGE_PATH / "processed"
    TEMP_DIR: Path = BASE_STORAGE_PATH / "temp"
    THUMBNAILS_DIR: Path = BASE_STORAGE_PATH / "thumbnails"
    
    # Chunked upload settings
    CHUNK_SIZE_MB: int = 5  # 5MB chunks
    ENABLE_CHUNKED_UPLOAD: bool = True
    CHUNK_UPLOAD_TIMEOUT_HOURS: int = 24
    
    # Video processing
    PROXY_HEIGHT: int = 720
    PROXY_CRF: int = 28  # Lower = better quality, higher file size
    THUMBNAIL_COUNT: int = 5  # Number of thumbnails to generate
    THUMBNAIL_HEIGHT: int = 180
    
    # Database
    DATABASE_URL: str = "sqlite:///./video_platform.db"
    DB_ECHO: bool = False  # Set True to see SQL queries
    
    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create storage directories
        for path in [self.UPLOAD_DIR, self.PROCESSED_DIR, self.TEMP_DIR, self.THUMBNAILS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    return Settings()