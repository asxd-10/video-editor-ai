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
    
    @staticmethod
    def upload_to_supabase_storage(
        file_path: str,
        bucket_name: str,
        folder_path: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Upload file to Supabase storage and return public URL.
        
        Uses separate Supabase credentials (SUPABASE_URL2, SUPABASE_KEY2) for storage operations
        if available, otherwise falls back to primary credentials.
        
        Args:
            file_path: Local path to file to upload
            bucket_name: Supabase storage bucket name
            folder_path: Optional folder path within bucket (e.g., "ai-edits/job_id")
            filename: Optional filename. If None, uses basename of file_path
            
        Returns:
            Public URL of uploaded file
        """
        import os
        from pathlib import Path
        
        # Get Supabase credentials (prioritize "2" versions for storage)
        supabase_url = os.getenv("SUPABASE_URL2") or os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY2") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY2") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured. Skipping upload. Set SUPABASE_URL2/SUPABASE_KEY2 or SUPABASE_URL/SUPABASE_KEY")
            return None  # Return None instead of raising error - upload is optional
        
        # Determine file path in storage
        if filename:
            storage_path = filename
        else:
            storage_path = Path(file_path).name
        
        if folder_path:
            # Normalize folder path (remove leading/trailing slashes)
            folder_path = folder_path.strip("/")
            storage_path = f"{folder_path}/{storage_path}"
        
        # Read file
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Try using supabase-py library first (if available)
        try:
            from supabase import create_client, Client
            logger.info("Using supabase-py library for upload")
            
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Upload using supabase-py
            with open(file_path_obj, "rb") as f:
                file_data = f.read()
            
            response = supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
            
            logger.info(f"File uploaded successfully via supabase-py: {public_url}")
            return public_url
            
        except ImportError:
            logger.info("supabase-py not available, using HTTP requests")
        except Exception as e:
            logger.warning(f"supabase-py upload failed: {e}, falling back to HTTP requests")
        
        # Fallback: Use direct HTTP requests (original method)
        with open(file_path_obj, "rb") as f:
            file_data = f.read()
        
        # Supabase Storage API: POST /storage/v1/object/{bucket}/{path}
        # URL encode the path segments but keep forward slashes
        from urllib.parse import quote
        
        # Encode each path segment separately, then join with /
        path_parts = storage_path.split('/')
        encoded_parts = [quote(part, safe='') for part in path_parts]
        encoded_storage_path = '/'.join(encoded_parts)
        
        upload_url = f"{supabase_url}/storage/v1/object/{bucket_name}/{encoded_storage_path}"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,  # Supabase requires both Authorization and apikey
            "Content-Type": "video/mp4",
            "x-upsert": "true"  # Overwrite if exists
        }
        
        logger.info(f"Uploading {file_path} to Supabase storage")
        logger.info(f"URL: {upload_url}")
        logger.info(f"File size: {len(file_data)} bytes, Bucket: {bucket_name}, Path: {storage_path} (encoded: {encoded_storage_path})")
        
        # Try POST (Supabase Storage API standard)
        try:
            response = requests.post(upload_url, data=file_data, headers=headers, timeout=600)
            if response.status_code >= 400:
                error_text = response.text[:1000] if response.text else "No error message"
                logger.error(f"POST upload failed ({response.status_code}): {error_text}")
                logger.error(f"Request URL: {upload_url}")
                logger.error(f"Storage path: {storage_path}")
                logger.error(f"Encoded path: {encoded_storage_path}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Log full error details for debugging
            if e.response:
                error_text = e.response.text[:1000] if e.response.text else "No error message"
                logger.error(f"HTTP Error {e.response.status_code}: {error_text}")
                logger.error(f"Request URL: {upload_url}")
                logger.error(f"Storage path: {storage_path}")
                logger.error(f"Bucket: {bucket_name}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
            raise
        
        # Construct public URL
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        
        logger.info(f"File uploaded successfully: {public_url}")
        return public_url