"""
Database models and operations using Supabase client
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import enum

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Supabase client
_supabase_client = None

def get_supabase_client():
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        try:
            import supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
            
            _supabase_client = supabase.create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except ImportError:
            raise ImportError("supabase library is required. Install it with: pip install supabase")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    return _supabase_client


# Enums
class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FrameStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Database operations using Supabase
class Database:
    """Database operations using Supabase client"""
    
    @staticmethod
    def get_client():
        return get_supabase_client()
    
    # Media operations
    @staticmethod
    def create_or_get_media(video_id: str, video_url: str, media_type: str = "video") -> Dict[str, Any]:
        """Create or get media record"""
        client = get_supabase_client()
        
        # Check if exists
        result = client.table("media").select("*").eq("video_id", video_id).execute()
        
        if result.data:
            return result.data[0]
        
        # Create new
        data = {
            "video_id": video_id,
            "video_url": video_url,
            "media_type": media_type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("media").insert(data).execute()
        return result.data[0] if result.data else data
    
    # Video Processing operations
    @staticmethod
    def create_or_get_video_processing(video_id: str, **kwargs) -> Dict[str, Any]:
        """Create or get video processing record, updating if exists"""
        client = get_supabase_client()
        
        result = client.table("video_processing").select("*").eq("video_id", video_id).execute()
        
        if result.data:
            # Update existing record
            update_data = {
                "status": kwargs.get("status", ProcessingStatus.PENDING.value),
                "granularity_seconds": kwargs.get("granularity_seconds", 1.0),
                "prompt": kwargs.get("prompt", "What's in this image?"),
                "model": kwargs.get("model", "google/gemini-2.0-flash-001"),
                "updated_at": datetime.utcnow().isoformat()
            }
            # Only update these if provided
            if "total_frames" in kwargs:
                update_data["total_frames"] = kwargs["total_frames"]
            if "processed_frames" in kwargs:
                update_data["processed_frames"] = kwargs["processed_frames"]
            if "failed_frames" in kwargs:
                update_data["failed_frames"] = kwargs["failed_frames"]
            
            updated = client.table("video_processing").update(update_data).eq("video_id", video_id).execute()
            return updated.data[0] if updated.data else result.data[0]
        
        data = {
            "video_id": video_id,
            "status": kwargs.get("status", ProcessingStatus.PENDING.value),
            "granularity_seconds": kwargs.get("granularity_seconds", 1.0),
            "prompt": kwargs.get("prompt", "What's in this image?"),
            "model": kwargs.get("model", "google/gemini-2.0-flash-001"),
            "total_frames": kwargs.get("total_frames", 0),
            "processed_frames": kwargs.get("processed_frames", 0),
            "failed_frames": kwargs.get("failed_frames", 0),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("video_processing").insert(data).execute()
        return result.data[0] if result.data else data
    
    @staticmethod
    def update_video_processing(video_id: str, **kwargs) -> Dict[str, Any]:
        """Update video processing record"""
        client = get_supabase_client()
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        result = client.table("video_processing").update(kwargs).eq("video_id", video_id).execute()
        return result.data[0] if result.data else {}
    
    # Image Processing operations
    @staticmethod
    def create_image_processing(video_id: str, **kwargs) -> Dict[str, Any]:
        """Create image processing record (allows multiple records per video_id)"""
        client = get_supabase_client()
        
        data = {
            "video_id": video_id,
            "status": kwargs.get("status", ProcessingStatus.COMPLETED.value),
            "prompt": kwargs.get("prompt", "What's in this image?"),
            "model": kwargs.get("model", "google/gemini-2.0-flash-001"),
            "llm_response": kwargs.get("llm_response", ""),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("image_processing").insert(data).execute()
        return result.data[0] if result.data else data
    
    @staticmethod
    def get_image_processing(video_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent image processing record for a video_id"""
        client = get_supabase_client()
        
        result = client.table("image_processing").select("*").eq("video_id", video_id).order("created_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def update_image_processing(video_id: str, **kwargs) -> Dict[str, Any]:
        """Update the most recent image processing record for a video_id"""
        client = get_supabase_client()
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        # Get the most recent record
        result = client.table("image_processing").select("*").eq("video_id", video_id).order("created_at", desc=True).limit(1).execute()
        
        if result.data:
            record_id = result.data[0].get("id")
            updated = client.table("image_processing").update(kwargs).eq("id", record_id).execute()
            return updated.data[0] if updated.data else {}
        return {}
    
    # Frame operations
    @staticmethod
    def create_frame(video_id: str, frame_number: int, timestamp_seconds: float, **kwargs) -> Dict[str, Any]:
        """Create frame record"""
        client = get_supabase_client()
        
        # Get media id
        media = Database.create_or_get_media(video_id, "")
        
        data = {
            "video_id": media.get("id"),  # Use media.id for foreign key
            "frame_number": frame_number,
            "timestamp_seconds": timestamp_seconds,
            "status": kwargs.get("status", FrameStatus.PENDING.value),
            "llm_response": kwargs.get("llm_response", ""),
            "error_message": kwargs.get("error_message"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("frames").insert(data).execute()
        return result.data[0] if result.data else data
    
    @staticmethod
    def update_frame(frame_id: int, **kwargs) -> Dict[str, Any]:
        """Update frame record"""
        client = get_supabase_client()
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        result = client.table("frames").update(kwargs).eq("id", frame_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def get_frames(video_id: str) -> List[Dict[str, Any]]:
        """Get all frames for a video"""
        client = get_supabase_client()
        media = Database.create_or_get_media(video_id, "")
        
        result = client.table("frames").select("*").eq("video_id", media.get("id")).order("frame_number").execute()
        return result.data if result.data else []
    
    # Scene Index operations
    @staticmethod
    def create_scene_index(video_id: str, video_db_id: str, index_id: str, **kwargs) -> Dict[str, Any]:
        """Create scene index record"""
        client = get_supabase_client()
        
        data = {
            "video_id": video_id,
            "video_db_id": video_db_id,
            "index_id": index_id,
            "extraction_type": kwargs.get("extraction_type", "shot_based"),
            "prompt": kwargs.get("prompt"),
            "status": kwargs.get("status", ProcessingStatus.PENDING.value),
            "scene_count": kwargs.get("scene_count", 0),
            "scenes_data": kwargs.get("scenes_data"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("scene_indexes").insert(data).execute()
        return result.data[0] if result.data else data
    
    @staticmethod
    def update_scene_index(video_id: str, index_id: str, **kwargs) -> Dict[str, Any]:
        """Update scene index record"""
        client = get_supabase_client()
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        result = client.table("scene_indexes").update(kwargs).eq("video_id", video_id).eq("index_id", index_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def get_scene_index(video_id: str, index_id: str) -> Optional[Dict[str, Any]]:
        """Get scene index record"""
        client = get_supabase_client()
        
        result = client.table("scene_indexes").select("*").eq("video_id", video_id).eq("index_id", index_id).execute()
        return result.data[0] if result.data else None
    
    # Transcription operations
    @staticmethod
    def create_transcription(video_id: str, video_db_id: str, **kwargs) -> Dict[str, Any]:
        """Create transcription record"""
        client = get_supabase_client()
        
        data = {
            "video_id": video_id,
            "video_db_id": video_db_id,
            "language_code": kwargs.get("language_code"),
            "status": kwargs.get("status", ProcessingStatus.PENDING.value),
            "transcript_data": kwargs.get("transcript_data"),
            "transcript_text": kwargs.get("transcript_text"),
            "segment_count": kwargs.get("segment_count", 0),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("transcriptions").insert(data).execute()
        return result.data[0] if result.data else data
    
    @staticmethod
    def update_transcription(video_id: str, **kwargs) -> Dict[str, Any]:
        """Update transcription record"""
        client = get_supabase_client()
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        
        result = client.table("transcriptions").update(kwargs).eq("video_id", video_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    def get_transcription(video_id: str) -> Optional[Dict[str, Any]]:
        """Get transcription record"""
        client = get_supabase_client()
        
        result = client.table("transcriptions").select("*").eq("video_id", video_id).execute()
        return result.data[0] if result.data else None
    
    # Processing Log operations
    @staticmethod
    def create_log(video_id: str, frame_id: Optional[int], level: str, message: str) -> Dict[str, Any]:
        """Create processing log"""
        client = get_supabase_client()
        
        # Get media id
        media = Database.create_or_get_media(video_id, "")
        
        data = {
            "video_id": media.get("id"),
            "frame_id": frame_id,
            "level": level,
            "message": message,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = client.table("processing_logs").insert(data).execute()
        return result.data[0] if result.data else data
    
    # Query operations
    @staticmethod
    def get_video_processing(video_id: str) -> Optional[Dict[str, Any]]:
        """Get video processing record"""
        client = get_supabase_client()
        
        result = client.table("video_processing").select("*").eq("video_id", video_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_media(video_id: str) -> Optional[Dict[str, Any]]:
        """Get media record"""
        client = get_supabase_client()
        
        result = client.table("media").select("*").eq("video_id", video_id).execute()
        return result.data[0] if result.data else None


# Initialize Supabase on import
def init_db():
    """Initialize Supabase client"""
    try:
        get_supabase_client()
        logger.info("Database (Supabase) initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


# Backward compatibility aliases
get_db_session = get_supabase_client
Media = type('Media', (), {'__getitem__': lambda self, key: None})  # Dummy class for compatibility
Video = type('Video', (), {'__getitem__': lambda self, key: None})
Frame = type('Frame', (), {'__getitem__': lambda self, key: None})
SceneIndex = type('SceneIndex', (), {'__getitem__': lambda self, key: None})
Transcription = type('Transcription', (), {'__getitem__': lambda self, key: None})
VideoProcessing = type('VideoProcessing', (), {'__getitem__': lambda self, key: None})
ImageProcessing = type('ImageProcessing', (), {'__getitem__': lambda self, key: None})
