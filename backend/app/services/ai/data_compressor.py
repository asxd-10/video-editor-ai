"""
Data Compression Service
Intelligently samples and compresses frame/scene data for LLM context
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataCompressor:
    """
    Compresses large video data (frames, scenes, transcript) into manageable LLM context.
    
    Strategies:
    - Temporal sampling (key moments, scene changes)
    - Importance-based selection (high-confidence frames)
    - Semantic clustering (similar frames/scenes)
    """
    
    def __init__(self, max_frames: int = 50, max_scenes: int = 20, max_transcript_segments: int = 100):
        """
        Args:
            max_frames: Maximum frames to include in LLM context
            max_scenes: Maximum scenes to include
            max_transcript_segments: Maximum transcript segments
        """
        self.max_frames = max_frames
        self.max_scenes = max_scenes
        self.max_transcript_segments = max_transcript_segments
    
    def compress_frames(
        self, 
        frames: List[Dict], 
        video_duration: float,
        strategy: str = "temporal_sampling"
    ) -> List[Dict]:
        """
        Compress frame data for LLM context.
        
        Args:
            frames: List of {frame_number, timestamp_seconds, llm_response, status}
            video_duration: Total video duration in seconds
            strategy: "temporal_sampling" | "importance_based" | "scene_based"
        
        Returns:
            Compressed list of frames
        """
        if not frames:
            return []
        
        # Filter only completed frames with valid responses
        # Support both formats: llm_response (ours) or description (friend's)
        # Filter: require description/llm_response, but status is optional (for API-provided data)
        logger.info(f"Compressing frames: {len(frames)} total frames received")
        valid_frames = [
            f for f in frames 
            if (f.get("llm_response") or f.get("description")) and 
               (f.get("status") is None or f.get("status") == "completed")
        ]
        
        logger.info(f"After filtering: {len(valid_frames)} valid frames (with description/llm_response)")
        
        if len(valid_frames) <= self.max_frames:
            return valid_frames
        
        if strategy == "temporal_sampling":
            return self._temporal_sampling(valid_frames, video_duration)
        elif strategy == "importance_based":
            return self._importance_based_sampling(valid_frames)
        elif strategy == "scene_based":
            return self._scene_based_sampling(valid_frames)
        else:
            return self._temporal_sampling(valid_frames, video_duration)
    
    def _temporal_sampling(self, frames: List[Dict], duration: float) -> List[Dict]:
        """Sample frames evenly across time + key moments"""
        if not frames:
            return []
        
        # Sort by timestamp (support both field names)
        sorted_frames = sorted(
            frames, 
            key=lambda x: x.get("timestamp_seconds") or x.get("frame_timestamp", 0)
        )
        
        # Strategy: Even distribution + beginning/end emphasis
        target_count = min(self.max_frames, len(sorted_frames))
        
        # Always include first and last frames
        selected = [sorted_frames[0]]
        
        if len(sorted_frames) > 1:
            selected.append(sorted_frames[-1])
        
        # Sample evenly across middle
        if len(sorted_frames) > 2 and target_count > 2:
            step = (len(sorted_frames) - 2) / (target_count - 2)
            for i in range(1, target_count - 1):
                idx = int(1 + i * step)
                if idx < len(sorted_frames) - 1:
                    selected.append(sorted_frames[idx])
        
        logger.info(f"Temporal sampling: selected {len(selected)} frames from {len(sorted_frames)} frames (target: {target_count})")
        
        # Remove duplicates based on timestamp (more reliable than id/frame_number which may be missing)
        seen_timestamps = set()
        unique_selected = []
        for frame in selected:
            timestamp = frame.get("timestamp_seconds") or frame.get("frame_timestamp", 0)
            # Use timestamp as unique identifier (round to 2 decimals to handle floating point issues)
            timestamp_key = round(timestamp, 2)
            if timestamp_key not in seen_timestamps:
                seen_timestamps.add(timestamp_key)
                unique_selected.append(frame)
        
        # Sort by timestamp
        return sorted(
            unique_selected, 
            key=lambda x: x.get("timestamp_seconds") or x.get("frame_timestamp", 0)
        )
    
    def _importance_based_sampling(self, frames: List[Dict]) -> List[Dict]:
        """Sample frames with longer/more detailed LLM responses (likely more important)"""
        # Sort by response length (proxy for importance/detail)
        # Support both llm_response (ours) and description (friend's)
        sorted_frames = sorted(
            frames, 
            key=lambda x: len(x.get("llm_response") or x.get("description", "")), 
            reverse=True
        )
        return sorted_frames[:self.max_frames]
    
    def _scene_based_sampling(self, frames: List[Dict]) -> List[Dict]:
        """Sample frames at scene boundaries"""
        # This would work with scenes data
        # For now, fallback to temporal
        return self._temporal_sampling(frames, 0)
    
    def compress_scenes(
        self, 
        scenes: List[Dict],
        strategy: str = "all"
    ) -> List[Dict]:
        """
        Compress scene data.
        
        Args:
            scenes: List of {start, end, description, ...}
            strategy: "all" | "key_moments" | "representative"
        
        Returns:
            Compressed scenes
        """
        if not scenes:
            return []
        
        # Parse scenes_data if it's a string
        if isinstance(scenes, list) and len(scenes) > 0:
            if isinstance(scenes[0].get("scenes_data"), str):
                import json
                try:
                    scenes = json.loads(scenes[0]["scenes_data"])
                except:
                    pass
        
        if len(scenes) <= self.max_scenes:
            return scenes
        
        if strategy == "all":
            # Return all if under limit
            return scenes[:self.max_scenes]
        elif strategy == "key_moments":
            # Prioritize longer scenes (likely more important)
            sorted_scenes = sorted(
                scenes,
                key=lambda x: (x.get("end", 0) - x.get("start", 0)),
                reverse=True
            )
            return sorted_scenes[:self.max_scenes]
        else:
            return scenes[:self.max_scenes]
    
    def compress_transcript(
        self,
        transcript_segments: List[Dict],
        strategy: str = "temporal"
    ) -> List[Dict]:
        """
        Compress transcript segments.
        
        Args:
            transcript_segments: List of {start, end, text, ...}
            strategy: "temporal" | "density" | "key_segments"
        
        Returns:
            Compressed transcript
        """
        if not transcript_segments:
            return []
        
        if len(transcript_segments) <= self.max_transcript_segments:
            return transcript_segments
        
        if strategy == "temporal":
            # Sample evenly across time
            step = len(transcript_segments) / self.max_transcript_segments
            selected = []
            for i in range(self.max_transcript_segments):
                idx = int(i * step)
                if idx < len(transcript_segments):
                    selected.append(transcript_segments[idx])
            return selected
        elif strategy == "density":
            # Prioritize segments with more words (denser content)
            sorted_segments = sorted(
                transcript_segments,
                key=lambda x: len(x.get("text", "").split()),
                reverse=True
            )
            return sorted_segments[:self.max_transcript_segments]
        else:
            return transcript_segments[:self.max_transcript_segments]
    
    def create_context_summary(
        self,
        frames: List[Dict],
        scenes: List[Dict],
        transcript_segments: List[Dict],
        video_duration: float
    ) -> Dict[str, Any]:
        """
        Create a compressed summary of all data for LLM context.
        
        Returns:
            {
                "frames": [...],  # Compressed
                "scenes": [...],   # Compressed
                "transcript": [...],  # Compressed
                "metadata": {
                    "total_frames": int,
                    "total_scenes": int,
                    "total_segments": int,
                    "compression_ratio": float
                }
            }
        """
        original_frame_count = len(frames) if frames else 0
        original_scene_count = len(scenes) if scenes else 0
        original_segment_count = len(transcript_segments) if transcript_segments else 0
        
        compressed_frames = self.compress_frames(frames, video_duration)
        compressed_scenes = self.compress_scenes(scenes)
        compressed_transcript = self.compress_transcript(transcript_segments)
        
        return {
            "frames": compressed_frames,
            "scenes": compressed_scenes,
            "transcript": compressed_transcript,
            "metadata": {
                "total_frames": original_frame_count,
                "total_scenes": original_scene_count,
                "total_segments": original_segment_count,
                "compressed_frames": len(compressed_frames),
                "compressed_scenes": len(compressed_scenes),
                "compressed_segments": len(compressed_transcript),
                "frame_compression_ratio": len(compressed_frames) / original_frame_count if original_frame_count > 0 else 1.0,
                "scene_compression_ratio": len(compressed_scenes) / original_scene_count if original_scene_count > 0 else 1.0,
                "transcript_compression_ratio": len(compressed_transcript) / original_segment_count if original_segment_count > 0 else 1.0
            }
        }

