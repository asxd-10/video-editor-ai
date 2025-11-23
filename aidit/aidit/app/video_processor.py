"""
VideoProcessor class for handling video splitting and frame extraction
"""
import cv2
import requests
import os
import base64
import logging
import tempfile
from typing import List, Tuple, Optional, Dict
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Class to handle video processing: downloading, splitting, and frame extraction
    """
    
    def __init__(self, video_index=None):
        """
        Initialize VideoProcessor
        
        Args:
            video_index: VideoIndex object for API calls
        """
        self.video_index = video_index
    
    def download_video(self, video_url: str, output_path: Optional[str] = None) -> str:
        """
        Download video from URL
        
        Args:
            video_url: URL of the video to download
            output_path: Optional path to save the video. If None, uses temp file
            
        Returns:
            Path to downloaded video file
        """
        try:
            logger.info(f"Downloading video from: {video_url}")
            
            if output_path is None:
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"video_{os.urandom(8).hex()}.mp4")
            
            response = requests.get(video_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Video downloaded to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def split_video_by_granularity(self, video_path: str, granularity_seconds: float = 1.0) -> List[Tuple[int, float, bytes]]:
        """
        Split video into frames based on granularity (seconds)
        
        Args:
            video_path: Path to video file
            granularity_seconds: Interval in seconds between frames
            
        Returns:
            List of tuples: (frame_number, timestamp_seconds, frame_bytes)
        """
        try:
            logger.info(f"Splitting video: {video_path} with granularity: {granularity_seconds}s")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * granularity_seconds)
            
            frames = []
            frame_number = 0
            current_time = 0.0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Only extract frame if it matches the granularity interval
                if frame_number % frame_interval == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PIL Image
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Convert to bytes
                    buffer = BytesIO()
                    pil_image.save(buffer, format='JPEG')
                    frame_bytes = buffer.getvalue()
                    
                    frames.append((len(frames), current_time, frame_bytes))
                    logger.debug(f"Extracted frame {len(frames)-1} at {current_time:.2f}s")
                
                frame_number += 1
                current_time = frame_number / fps
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video")
            return frames
            
        except Exception as e:
            logger.error(f"Error splitting video: {str(e)}")
            raise
    
    def frame_bytes_to_base64(self, frame_bytes: bytes) -> str:
        """
        Convert frame bytes to base64 data URL
        
        Args:
            frame_bytes: Image bytes
            
        Returns:
            Base64 data URL string
        """
        base64_image = base64.b64encode(frame_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_image}"
    
    def process_video(self, video_url: str, granularity_seconds: float = 1.0, 
                     prompt: str = "What's in this image?", 
                     model: str = "google/gemini-2.0-flash-001") -> List[Dict]:
        """
        Complete video processing pipeline: download, split, and process frames
        
        Args:
            video_url: URL of video to process
            granularity_seconds: Interval between frames
            prompt: Prompt for LLM
            model: Model to use
            
        Returns:
            List of processing results for each frame
        """
        video_path = None
        try:
            # Download video
            video_path = self.download_video(video_url)
            
            # Split video into frames
            frames = self.split_video_by_granularity(video_path, granularity_seconds)
            
            # Process each frame if video_index is available
            results = []
            if self.video_index:
                for frame_num, timestamp, frame_bytes in frames:
                    try:
                        base64_image = self.frame_bytes_to_base64(frame_bytes)
                        result = self.video_index.process_image_from_base64(base64_image, prompt)
                        results.append({
                            "frame_number": frame_num,
                            "timestamp": timestamp,
                            "result": result
                        })
                    except Exception as e:
                        logger.error(f"Error processing frame {frame_num}: {str(e)}")
                        results.append({
                            "frame_number": frame_num,
                            "timestamp": timestamp,
                            "error": str(e)
                        })
            else:
                # Just return frame info without processing
                results = [
                    {
                        "frame_number": frame_num,
                        "timestamp": timestamp,
                        "frame_size": len(frame_bytes)
                    }
                    for frame_num, timestamp, frame_bytes in frames
                ]
            
            return results
            
        finally:
            # Clean up downloaded video file
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"Cleaned up video file: {video_path}")
                except Exception as e:
                    logger.warning(f"Could not remove video file: {str(e)}")

