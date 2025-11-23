from pathlib import Path
from typing import BinaryIO, Optional
import os
import shutil
import requests
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
    
    @staticmethod
    def download_video_from_url(video_url: str, video_id: str, filename: Optional[str] = None) -> str:
        """
        Download video from URL (S3 or HTTP) and cache it locally.
        
        Args:
            video_url: URL of the video to download
            video_id: Video ID for organizing cached files
            filename: Optional filename. If None, extracts from URL or uses default
            
        Returns:
            Path to downloaded video file
        """
        try:
            # Determine output path
            cache_dir = settings.TEMP_DIR / video_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            if filename:
                output_path = cache_dir / filename
            else:
                # Try to extract filename from URL, or use default
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(video_url)
                    url_filename = os.path.basename(parsed.path)
                    if url_filename and '.' in url_filename:
                        output_path = cache_dir / url_filename
                    else:
                        output_path = cache_dir / "cached_video.mp4"
                except:
                    output_path = cache_dir / "cached_video.mp4"
            
            # Check if file already exists (cached)
            if output_path.exists():
                logger.info(f"Using cached video file: {output_path}")
                return str(output_path)
            
            logger.info(f"Downloading video from URL: {video_url[:80]}...")
            logger.info(f"Caching to: {output_path}")
            
            # Download with streaming to handle large files
            response = requests.get(video_url, stream=True, timeout=600)  # 10 minute timeout
            response.raise_for_status()
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if downloaded % (10 * 1024 * 1024) == 0:  # Log every 10MB
                                logger.info(f"Downloaded {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB ({percent:.1f}%)")
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Video downloaded and cached: {output_path} ({file_size / (1024*1024):.1f}MB)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to download video from URL: {e}")
            raise