"""
Data Loader Service
Loads data from Supabase tables (media, transcriptions, frames, scenes)
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads video data from Supabase tables.
    Handles the new schema: media, transcriptions, frames, scenes
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_media(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Load media record by video_id.
        
        Args:
            video_id: Video ID (text field in media table)
        
        Returns:
            Media record or None
        """
        try:
            result = self.db.execute(
                text("SELECT * FROM media WHERE video_id = :video_id"),
                {"video_id": video_id}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.error(f"Failed to load media for {video_id}: {e}")
            return None
    
    def load_transcription(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Load transcription record by video_id.
        
        Args:
            video_id: Video ID (text field in transcriptions table)
        
        Returns:
            Transcription record or None
        """
        try:
            result = self.db.execute(
                text("SELECT * FROM transcriptions WHERE video_id = :video_id"),
                {"video_id": video_id}
            )
            row = result.fetchone()
            if row:
                record = dict(row._mapping)
                # Parse transcript_data if it's a string
                if isinstance(record.get("transcript_data"), str):
                    try:
                        record["transcript_data"] = json.loads(record["transcript_data"])
                    except:
                        pass
                return record
            return None
        except Exception as e:
            logger.error(f"Failed to load transcription for {video_id}: {e}")
            return None
    
    def load_frames(self, video_id: str) -> List[Dict[str, Any]]:
        """
        Load frames for a media record.
        
        Handles both formats:
        - Our format: {timestamp_seconds, llm_response, ...}
        - Friend's format: {frame_timestamp, description, ...}
        
        Args:
            video_id: Video ID (TEXT, references media.video_id)
        
        Returns:
            List of frame records (normalized format)
        """
        try:
            result = self.db.execute(
                text("SELECT * FROM frames WHERE video_id = :video_id ORDER BY timestamp_seconds"),
                {"video_id": video_id}
            )
            rows = result.fetchall()
            frames = [dict(row._mapping) for row in rows]
            
            # Normalize format: handle friend's format (frame_timestamp → timestamp_seconds, description → llm_response)
            normalized = []
            for frame in frames:
                normalized_frame = dict(frame)
                
                # Map frame_timestamp → timestamp_seconds (if friend's format)
                if "frame_timestamp" in normalized_frame and "timestamp_seconds" not in normalized_frame:
                    normalized_frame["timestamp_seconds"] = normalized_frame.pop("frame_timestamp")
                
                # Map description → llm_response (if friend's format and llm_response missing)
                if "description" in normalized_frame and not normalized_frame.get("llm_response"):
                    normalized_frame["llm_response"] = normalized_frame.get("description")
                
                normalized.append(normalized_frame)
            
            return normalized
        except Exception as e:
            logger.error(f"Failed to load frames for video_id {video_id}: {e}")
            return []
    
    def load_scenes(self, video_id: str) -> List[Dict[str, Any]]:
        """
        Load scenes for a video from scene_indexes table.
        
        Note: The unified schema uses `scene_indexes` table with:
        - video_id (text)
        - scenes_data (JSONB)
        
        Args:
            video_id: Video ID
        
        Returns:
            List of scene records (parsed from scenes_data)
        """
        try:
            # Query scene_indexes table (unified schema)
            result = self.db.execute(
                text("SELECT * FROM scene_indexes WHERE video_id = :video_id AND status = 'completed' ORDER BY created_at DESC"),
                {"video_id": video_id}
            )
            rows = result.fetchall()
            
            scenes = []
            for row in rows:
                record = dict(row._mapping)
                # Extract scenes_data (JSONB field)
                scenes_data = record.get("scenes_data")
                
                if scenes_data:
                    # scenes_data is already a dict/list (JSONB is parsed by SQLAlchemy)
                    if isinstance(scenes_data, list):
                        # If it's a list of scenes, add them
                        for scene in scenes_data:
                            if isinstance(scene, dict):
                                # Add video_id and other metadata to each scene
                                scene["video_id"] = video_id
                                scene["index_id"] = record.get("index_id")
                                scenes.append(scene)
                            else:
                                scenes.append({"data": scene, "video_id": video_id})
                    elif isinstance(scenes_data, dict):
                        # If it's a dict, check if it has a 'scenes' key
                        if "scenes" in scenes_data and isinstance(scenes_data["scenes"], list):
                            scenes.extend(scenes_data["scenes"])
                        else:
                            # Treat the whole dict as a scene
                            scenes_data["video_id"] = video_id
                            scenes.append(scenes_data)
            
            return scenes
        except Exception as e:
            logger.warning(f"Failed to load scenes for {video_id}: {e} (table might not exist)")
            # Rollback the failed transaction to allow subsequent queries
            try:
                self.db.rollback()
            except:
                pass
            return []
    
    def load_all_data(self, video_id: str) -> Dict[str, Any]:
        """
        Load all data for a video (media, transcription, frames, scenes).
        
        Args:
            video_id: Video ID from media table (text field)
        
        Returns:
            {
                "media": {...},
                "transcription": {...},
                "frames": [...],
                "scenes": [...],
                "video_duration": float
            }
        """
        # Load media (this is the source of truth)
        media = self.load_media(video_id)
        if not media:
            raise ValueError(f"Media not found for video_id: {video_id}")
        
        # Load transcription (uses video_id text field)
        transcription = self.load_transcription(video_id)
        
        # Load frames (uses video_id text field - references media.video_id)
        frames = self.load_frames(video_id)
        
        # Load scenes (uses video_id text field)
        scenes = self.load_scenes(video_id)
        
        # Extract video duration (try multiple sources, prioritize media table)
        video_duration = 0.0
        
        # First: Try media.duration_seconds (most reliable)
        if media.get("duration_seconds"):
            video_duration = float(media["duration_seconds"])
        elif media.get("duration"):
            video_duration = float(media["duration"])
        
        # Fallback: Try transcript segments
        if video_duration == 0.0 and transcription and transcription.get("transcript_data"):
            transcript_data = transcription["transcript_data"]
            if isinstance(transcript_data, list) and len(transcript_data) > 0:
                last_segment = transcript_data[-1]
                if isinstance(last_segment, dict):
                    video_duration = last_segment.get("end", 0.0)
        
        # Last resort: Try frames
        if video_duration == 0.0 and frames:
            video_duration = max(f.get("timestamp_seconds", 0.0) for f in frames) if frames else 0.0
        
        return {
            "media": media,
            "transcription": transcription,
            "frames": frames,
            "scenes": scenes,
            "video_duration": video_duration
        }
    
    def extract_transcript_segments(self, transcription: Optional[Dict]) -> List[Dict[str, Any]]:
        """
        Extract transcript segments from transcription record.
        
        Args:
            transcription: Transcription record (dict) or list of records
        
        Returns:
            List of segments [{start, end, text, ...}]
        """
        if not transcription:
            return []
        
        # Handle case where transcription is already a list (shouldn't happen, but be defensive)
        if isinstance(transcription, list):
            # If it's a list, extract segments from all transcriptions
            all_segments = []
            for trans in transcription:
                if isinstance(trans, dict):
                    segments = self.extract_transcript_segments(trans)
                    all_segments.extend(segments)
            return all_segments
        
        # transcription should be a dict
        if not isinstance(transcription, dict):
            logger.warning(f"Unexpected transcription type: {type(transcription)}")
            return []
        
        transcript_data = transcription.get("transcript_data")
        if not transcript_data:
            return []
        
        # If it's already a list, return it
        if isinstance(transcript_data, list):
            return transcript_data
        
        # If it's a dict with segments key
        if isinstance(transcript_data, dict):
            segments = transcript_data.get("segments", [])
            if isinstance(segments, list):
                return segments
        
        return []
    
    def load_all_data_multi(self, video_ids: List[str]) -> Dict[str, Any]:
        """
        Load all data for multiple videos and combine them intelligently.
        
        Args:
            video_ids: List of video IDs from media table
        
        Returns:
            {
                "media": [{...}, {...}],  # List of media records
                "transcription": [{...}, {...}],  # List of transcriptions
                "frames": [...],  # Combined frames with video_id tag
                "scenes": [...],  # Combined scenes with video_id tag
                "video_duration": float,  # Total combined duration
                "videos": [  # Per-video metadata
                    {"video_id": "...", "duration": float, "frames_count": int, ...}
                ]
            }
        """
        if not video_ids:
            raise ValueError("video_ids list cannot be empty")
        
        all_media = []
        all_transcriptions = []
        all_frames = []
        all_scenes = []
        videos_metadata = []
        total_duration = 0.0
        
        # Load data for each video
        for video_id in video_ids:
            media = self.load_media(video_id)
            if not media:
                logger.warning(f"Media not found for video_id: {video_id}, skipping")
                continue
            
            transcription = self.load_transcription(video_id)
            frames = self.load_frames(video_id)
            scenes = self.load_scenes(video_id)
            
            # Calculate video duration
            video_duration = 0.0
            if media.get("duration_seconds"):
                video_duration = float(media["duration_seconds"])
            elif media.get("duration"):
                video_duration = float(media["duration"])
            
            # Tag frames and scenes with video_id for tracking
            tagged_frames = []
            for frame in frames:
                tagged_frame = dict(frame)
                tagged_frame["source_video_id"] = video_id
                tagged_frames.append(tagged_frame)
            
            tagged_scenes = []
            for scene in scenes:
                tagged_scene = dict(scene)
                tagged_scene["source_video_id"] = video_id
                tagged_scenes.append(tagged_scene)
            
            all_media.append(media)
            all_transcriptions.append(transcription)
            all_frames.extend(tagged_frames)
            all_scenes.extend(tagged_scenes)
            total_duration += video_duration
            
            videos_metadata.append({
                "video_id": video_id,
                "duration": video_duration,
                "frames_count": len(frames),
                "scenes_count": len(scenes),
                "has_transcription": bool(transcription),
                "title": media.get("title", ""),
                "video_url": media.get("video_url"),
                "original_path": media.get("original_path")
            })
        
        if not all_media:
            raise ValueError(f"No valid media found for video_ids: {video_ids}")
        
        # Sort frames by timestamp (across all videos)
        all_frames.sort(key=lambda f: f.get("timestamp_seconds", 0.0))
        
        # Sort scenes by start time (across all videos)
        all_scenes.sort(key=lambda s: s.get("start", 0.0))
        
        return {
            "media": all_media,
            "transcription": all_transcriptions,
            "frames": all_frames,
            "scenes": all_scenes,
            "video_duration": total_duration,
            "videos": videos_metadata,
            "video_ids": video_ids  # Keep track of which videos were used
        }

