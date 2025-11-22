from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Video Upload Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Security
    ALLOWED_ORIGINS: list = []  # Will be set dynamically
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: list = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    ALLOWED_MIME_TYPES: list = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm"]
    
    # Storage - Use /opt/render/project/src for Render persistent disk
    BASE_STORAGE_PATH: Path = Path(os.getenv("STORAGE_PATH", "../storage"))
    UPLOAD_DIR: Path = None
    PROCESSED_DIR: Path = None
    TEMP_DIR: Path = None
    THUMBNAILS_DIR: Path = None
    
    # Chunked upload settings
    CHUNK_SIZE_MB: int = 5
    ENABLE_CHUNKED_UPLOAD: bool = True
    CHUNK_UPLOAD_TIMEOUT_HOURS: int = 24
    
    # Video processing
    PROXY_HEIGHT: int = 720
    PROXY_CRF: int = 28
    THUMBNAIL_COUNT: int = 5
    THUMBNAIL_HEIGHT: int = 180
    
    # Database
    DATABASE_URL: str = "sqlite:///./video_platform.db"
    DB_ECHO: bool = False
    
    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = None
    CELERY_RESULT_BACKEND: str = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set up storage paths
        self.UPLOAD_DIR = self.BASE_STORAGE_PATH / "uploads"
        self.PROCESSED_DIR = self.BASE_STORAGE_PATH / "processed"
        self.TEMP_DIR = self.BASE_STORAGE_PATH / "temp"
        self.THUMBNAILS_DIR = self.BASE_STORAGE_PATH / "thumbnails"
        
        # Create storage directories
        for path in [self.UPLOAD_DIR, self.PROCESSED_DIR, self.TEMP_DIR, self.THUMBNAILS_DIR]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Set Celery URLs if not provided
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        
        # Set CORS origins dynamically
        if self.ENVIRONMENT == "production":
            # Will be set by RENDER_EXTERNAL_URL
            frontend_url = os.getenv("FRONTEND_URL")
            if frontend_url:
                self.ALLOWED_ORIGINS = [frontend_url]
        else:
            self.ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

@lru_cache()
def get_settings() -> Settings:
    return Settings()