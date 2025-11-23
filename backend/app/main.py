from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import upload, edit, ai_edit, unified_ai_edit
from app.database import engine, Base
from app.config import get_settings
# Import all models to ensure they're registered with Base
from app.models import (
    Video, VideoAsset, UploadChunk, ProcessingLog,
    Transcript, ClipCandidate, EditJob, RetentionAnalysis, AIEditJob
)
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Dynamic CORS
origins = settings.ALLOWED_ORIGINS
if not origins:
    # Allow all origins in development
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/storage", StaticFiles(directory=str(settings.BASE_STORAGE_PATH)), name="storage")

# Include routers
app.include_router(upload.router, prefix="/api/videos", tags=["videos"])
app.include_router(edit.router, prefix="/api/videos", tags=["editing"])
app.include_router(ai_edit.router, prefix="/api/videos", tags=["ai-editing"])
app.include_router(unified_ai_edit.router, prefix="/api", tags=["unified-ai-edit"])

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}