from pathlib import Path
from typing import BinaryIO
import os
import shutil
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class StorageService:
    """Handle file storage operations"""
    
    @staticmethod
    def get_video_directory(video_id: str) -> Path:
        """Get dedicated directory for a video"""
        path = settings.UPLOAD_DIR / video_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_processed_directory(video_id: str) -> Path:
        """Get directory for processed assets"""
        path = settings.PROCESSED_DIR / video_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def save_upload(
        file: BinaryIO, 
        video_id: str, 
        filename: str
    ) -> str:
        """
        Save uploaded file
        Returns: absolute path to saved file
        """
        try:
            directory = StorageService.get_video_directory(video_id)
            file_path = directory / filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            
            logger.info(f"Saved upload: {file_path} ({os.path.getsize(file_path)} bytes)")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save upload: {str(e)}")
            raise
    
    @staticmethod
    def save_chunk(
        chunk: bytes,
        video_id: str,
        chunk_number: int
    ) -> str:
        """Save upload chunk to temp directory"""
        temp_dir = settings.TEMP_DIR / video_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_path = temp_dir / f"chunk_{chunk_number:04d}"
        with open(chunk_path, "wb") as f:
            f.write(chunk)
        
        return str(chunk_path)
    
    @staticmethod
    def assemble_chunks(
        video_id: str,
        total_chunks: int,
        output_filename: str
    ) -> str:
        """Assemble chunks into final file"""
        temp_dir = settings.TEMP_DIR / video_id
        output_dir = StorageService.get_video_directory(video_id)
        output_path = output_dir / output_filename
        
        with open(output_path, "wb") as outfile:
            for i in range(total_chunks):
                chunk_path = temp_dir / f"chunk_{i:04d}"
                if not chunk_path.exists():
                    raise FileNotFoundError(f"Missing chunk {i}")
                
                with open(chunk_path, "rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, outfile)
        
        # Clean up chunks
        shutil.rmtree(temp_dir)
        
        return str(output_path)
    
    @staticmethod
    def delete_video(video_id: str):
        """Delete all files associated with a video"""
        for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.TEMP_DIR]:
            video_dir = directory / video_id
            if video_dir.exists():
                shutil.rmtree(video_dir)
                logger.info(f"Deleted directory: {video_dir}")