"""
SceneIndexer class for video scene extraction using videodb
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

try:
    import videodb
    from videodb import SceneExtractionType
    VIDEODB_AVAILABLE = True
except ImportError:
    VIDEODB_AVAILABLE = False
    logging.warning("videodb not installed. Scene indexing will not work.")

logger = logging.getLogger(__name__)


class SceneIndexer:
    """
    Class to handle video scene extraction using videodb
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SceneIndexer
        
        Args:
            api_key: videodb API key (defaults to environment variable)
        """
        if not VIDEODB_AVAILABLE:
            raise ImportError("videodb package is required. Install it with: pip install videodb")
        
        self.api_key = api_key or os.getenv("VIDEODB_API_KEY")
        if not self.api_key:
            raise ValueError("VIDEODB_API_KEY must be set in environment or passed as parameter")
        
        self.conn = videodb.connect(api_key=self.api_key)
        logger.info("SceneIndexer initialized")
    
    def upload_video(self, video_path_or_url: str) -> Any:
        """
        Upload a video file or URL to videodb
        
        Args:
            video_path_or_url: Path to the video file or URL (S3, HTTP, etc.)
            
        Returns:
            Video file object from videodb
        """
        try:
            logger.info(f"Uploading video: {video_path_or_url}")
            
            # Check if it's a URL (starts with http://, https://, or s3://)
            is_url = video_path_or_url.startswith(('http://', 'https://', 's3://'))
            
            if is_url:
                # Upload directly from URL
                video_file = self.conn.upload(video_path_or_url)
            else:
                # Upload from local file path
                if not os.path.exists(video_path_or_url):
                    raise FileNotFoundError(f"Video file not found: {video_path_or_url}")
                video_file = self.conn.upload(video_path_or_url)
            
            logger.info(f"Video uploaded successfully: {video_file.id}")
            return video_file
            
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise
    
    def index_scenes(
        self,
        video_file_obj,
        extraction_type: str = "shot_based",
        extraction_config: Optional[Dict[str, Any]] = None,
        prompt: str = "describe the image in 100 words",
        callback_url: Optional[str] = None
    ) -> str:
        """
        Index scenes from a video
        
        Args:
            video_file_obj: Video file object from videodb (returned by upload)
            extraction_type: Type of extraction ("shot_based" or "time_based")
            extraction_config: Configuration for extraction
            prompt: Prompt for scene description
            callback_url: Optional callback URL for async processing
            
        Returns:
            Index ID for the scene index
        """
        try:
            logger.info(f"Indexing scenes for video: {video_file_obj.id}")
            
            # Map extraction type string to enum
            if extraction_type == "shot_based":
                scene_type = SceneExtractionType.shot_based
            elif extraction_type == "time_based":
                scene_type = SceneExtractionType.time_based
            else:
                raise ValueError(f"Unknown extraction type: {extraction_type}")
            
            # Default extraction config
            if extraction_config is None:
                if extraction_type == "shot_based":
                    extraction_config = {"threshold": 20, "frame_count": 5}
                else:
                    extraction_config = {}
            
            # Build index_scenes arguments
            index_args = {
                "extraction_type": scene_type,
                "extraction_config": extraction_config,
                "prompt": prompt
            }
            
            # Add callback_url if provided
            if callback_url:
                index_args["callback_url"] = callback_url
            
            # Index scenes
            index_id = video_file_obj.index_scenes(**index_args)
            
            logger.info(f"Scene indexing started. Index ID: {index_id}")
            return index_id
            
        except Exception as e:
            logger.error(f"Error indexing scenes: {str(e)}")
            raise
    
    def get_scene_index(self, video_file_obj, index_id: str) -> List[Dict[str, Any]]:
        """
        Get scene index results
        
        Args:
            video_file_obj: Video file object from videodb (returned by upload)
            index_id: Index ID from index_scenes
            
        Returns:
            List of scene descriptions with start/end times
        """
        try:
            logger.info(f"Getting scene index for video: {video_file_obj.id}, index: {index_id}")
            
            scene_index = video_file_obj.get_scene_index(index_id)
            
            logger.info(f"Retrieved {len(scene_index)} scenes")
            return scene_index
            
        except Exception as e:
            logger.error(f"Error getting scene index: {str(e)}")
            raise
    
    def index_spoken_words(
        self,
        video_file_obj,
        language_code: Optional[str] = None,
        force: bool = False,
        callback_url: Optional[str] = None
    ) -> None:
        """
        Index spoken words in a video
        
        Args:
            video_file_obj: Video file object from videodb (returned by upload)
            language_code: Optional language code for transcription
            force: Force re-indexing if already exists
            callback_url: Optional callback URL for async processing
            
        Returns:
            None (uses callback for async processing)
        """
        try:
            logger.info(f"Indexing spoken words for video: {video_file_obj.id}")
            
            # Build index_spoken_words arguments
            index_args = {
                "force": force
            }
            
            if language_code:
                index_args["language_code"] = language_code
            
            if callback_url:
                index_args["callback_url"] = callback_url
            
            # Index spoken words
            video_file_obj.index_spoken_words(**index_args)
            
            logger.info("Spoken words indexing started")
            
        except Exception as e:
            logger.error(f"Error indexing spoken words: {str(e)}")
            raise
    
    def get_transcript(self, video_file_obj) -> List[Dict[str, Any]]:
        """
        Get transcript for a video
        
        Args:
            video_file_obj: Video file object from videodb (returned by upload)
            
        Returns:
            List of transcript segments with start, end, text, and optional speaker
        """
        try:
            logger.info(f"Getting transcript for video: {video_file_obj.id}")
            
            transcript = video_file_obj.get_transcript()
            
            logger.info(f"Retrieved transcript with {len(transcript)} segments")
            return transcript
            
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            raise

