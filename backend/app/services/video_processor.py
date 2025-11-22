import ffmpeg
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Comprehensive video processing utilities"""
    
    @staticmethod
    def calculate_md5(file_path: str, chunk_size: int = 8192) -> str:
        """Calculate MD5 checksum of file"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    @staticmethod
    def extract_metadata(video_path: str) -> Dict:
        """
        Extract comprehensive video metadata
        Returns: {duration, fps, width, height, video_codec, audio_codec, 
                  bitrate, has_audio, aspect_ratio}
        """
        try:
            probe = ffmpeg.probe(video_path)
            
            # Get video stream
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'), 
                None
            )
            
            # Get audio stream
            audio_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'audio'), 
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            # Calculate aspect ratio
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            aspect_ratio = f"{width}:{height}"
            if width and height:
                from math import gcd
                divisor = gcd(width, height)
                aspect_ratio = f"{width//divisor}:{height//divisor}"
            
            # Parse FPS
            fps_str = video_stream.get('r_frame_rate', '0/1')
            fps = eval(fps_str) if '/' in fps_str else float(fps_str)
            
            metadata = {
                "duration": float(probe['format'].get('duration', 0)),
                "fps": round(fps, 2),
                "width": width,
                "height": height,
                "video_codec": video_stream.get('codec_name', 'unknown'),
                "audio_codec": audio_stream.get('codec_name', 'none') if audio_stream else None,
                "bitrate": int(probe['format'].get('bit_rate', 0)) // 1000,  # kbps
                "has_audio": audio_stream is not None,
                "aspect_ratio": aspect_ratio
            }
            
            logger.info(f"Extracted metadata from {video_path}: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed for {video_path}: {str(e)}")
            raise Exception(f"Metadata extraction failed: {str(e)}")
    
    @staticmethod
    def create_proxy(
        input_path: str, 
        output_path: str, 
        height: int = 720, 
        crf: int = 28
    ) -> Dict:
        """
        Create a lower-resolution proxy video for UI playback
        Returns: {width, height, file_size, duration}
        """
        try:
            logger.info(f"Creating proxy: {input_path} -> {output_path}")
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create proxy with optimized settings
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                vf=f'scale=-2:{height}',  # Maintain aspect ratio
                crf=crf,
                preset='medium',  # Balance between speed and quality
                movflags='faststart',  # Enable streaming
                acodec='aac',
                audio_bitrate='128k'
            )
            
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Get proxy metadata
            probe = ffmpeg.probe(output_path)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            result = {
                "width": int(video_stream['width']),
                "height": int(video_stream['height']),
                "file_size": os.path.getsize(output_path),
                "duration": float(probe['format']['duration'])
            }
            
            logger.info(f"Proxy created successfully: {result}")
            return result
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Proxy creation failed: {error_msg}")
            raise Exception(f"Proxy creation failed: {error_msg}")
    
    @staticmethod
    def extract_thumbnails(
        input_path: str,
        output_dir: str,
        count: int = 5,
        height: int = 180
    ) -> list:
        """
        Extract evenly-spaced thumbnails from video
        Returns: list of thumbnail paths
        """
        try:
            logger.info(f"Extracting {count} thumbnails from {input_path}")
            
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Get video duration
            probe = ffmpeg.probe(input_path)
            duration = float(probe['format']['duration'])
            
            thumbnails = []
            interval = duration / (count + 1)  # Avoid first/last frame
            
            for i in range(1, count + 1):
                timestamp = interval * i
                output_path = f"{output_dir}/thumb_{i:02d}.jpg"
                
                try:
                    (
                        ffmpeg
                        .input(input_path, ss=timestamp)
                        .filter('scale', -2, height)
                        .output(output_path, vframes=1, format='image2', **{'q:v': 2})
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    thumbnails.append(output_path)
                except ffmpeg.Error as e:
                    logger.warning(f"Failed to extract thumbnail at {timestamp}s: {e}")
                    continue
            
            logger.info(f"Extracted {len(thumbnails)} thumbnails")
            return thumbnails
            
        except Exception as e:
            logger.error(f"Thumbnail extraction failed: {str(e)}")
            raise Exception(f"Thumbnail extraction failed: {str(e)}")
    
    @staticmethod
    def validate_video(file_path: str) -> bool:
        """
        Validate that file is a proper video
        Returns: True if valid, raises Exception otherwise
        """
        try:
            probe = ffmpeg.probe(file_path)
            
            # Check for video stream
            has_video = any(s['codec_type'] == 'video' for s in probe['streams'])
            if not has_video:
                raise ValueError("No video stream found in file")
            
            # Check duration
            duration = float(probe['format'].get('duration', 0))
            if duration <= 0:
                raise ValueError("Invalid video duration")
            
            return True
            
        except ffmpeg.Error as e:
            raise ValueError(f"Invalid video file: {e.stderr.decode()}")