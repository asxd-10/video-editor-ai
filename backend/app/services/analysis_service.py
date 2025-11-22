import ffmpeg
import numpy as np
from pathlib import Path
from scenedetect import detect, ContentDetector
# Keep old imports for fallback
try:
    from scenedetect import VideoManager, SceneManager
except ImportError:
    VideoManager = None
    SceneManager = None
from app.config import get_settings
import logging
import torch
import torchaudio
try:
    import silero_vad
    SILERO_VAD_AVAILABLE = True
except ImportError:
    SILERO_VAD_AVAILABLE = False

logger = logging.getLogger(__name__)
settings = get_settings()

class AnalysisService:
    def __init__(self):
        """Initialize analysis service with VAD model"""
        self.vad_model = None
        self.vad_utils = None
        if SILERO_VAD_AVAILABLE:
            try:
                # Try different import patterns for silero-vad
                if hasattr(silero_vad, 'load_silero_vad_model'):
                    result = silero_vad.load_silero_vad_model()
                    if isinstance(result, tuple):
                        self.vad_model, self.vad_utils = result
                    else:
                        self.vad_model = result
                elif hasattr(silero_vad, 'load_model'):
                    self.vad_model = silero_vad.load_model()
                
                if self.vad_model is not None:
                    logger.info("Silero VAD model loaded successfully")
                else:
                    logger.warning("VAD model load returned None, using fallback")
            except Exception as e:
                logger.warning(f"Failed to load Silero VAD model: {e}. Will use fallback method.")
                self.vad_model = None
        else:
            logger.warning("Silero VAD not available, will use fallback method")
    
    def detect_silence(self, audio_path: str, min_silence_duration_ms: int = 600) -> list:
        """
        Detect silence segments in audio using Silero VAD.
        Returns: [(start_seconds, end_seconds), ...]
        """
        try:
            if self.vad_model is None or not SILERO_VAD_AVAILABLE:
                logger.warning("VAD model not available, using fallback method")
                return self._detect_silence_fallback(audio_path, min_silence_duration_ms)
            
            # Load audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Get speech timestamps (non-speech = silence)
            if hasattr(silero_vad, 'get_speech_timestamps'):
                speech_timestamps = silero_vad.get_speech_timestamps(
                    waveform,
                    self.vad_model,
                    threshold=0.5,
                    sampling_rate=sample_rate,
                    return_seconds=True
                )
            elif hasattr(self.vad_utils, 'get_speech_timestamps'):
                speech_timestamps = self.vad_utils.get_speech_timestamps(
                    waveform,
                    self.vad_model,
                    threshold=0.5,
                    sampling_rate=sample_rate,
                    return_seconds=True
                )
            else:
                raise ValueError("Cannot find get_speech_timestamps function")
            
            # Convert speech segments to silence segments
            silence_segments = []
            video_duration = waveform.shape[1] / sample_rate
            
            if not speech_timestamps:
                # Entire video is silence
                return [(0.0, video_duration)]
            
            # Check for silence at the beginning
            if speech_timestamps[0]['start'] > min_silence_duration_ms / 1000.0:
                silence_segments.append((0.0, speech_timestamps[0]['start']))
            
            # Check for silence between speech segments
            for i in range(len(speech_timestamps) - 1):
                gap_start = speech_timestamps[i]['end']
                gap_end = speech_timestamps[i + 1]['start']
                gap_duration = gap_end - gap_start
                
                if gap_duration >= min_silence_duration_ms / 1000.0:
                    silence_segments.append((gap_start, gap_end))
            
            # Check for silence at the end
            last_speech_end = speech_timestamps[-1]['end']
            if video_duration - last_speech_end > min_silence_duration_ms / 1000.0:
                silence_segments.append((last_speech_end, video_duration))
            
            logger.info(f"Detected {len(silence_segments)} silence segments")
            return silence_segments
            
        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            # Fallback to simple method
            return self._detect_silence_fallback(audio_path, min_silence_duration_ms)
    
    def _detect_silence_fallback(self, audio_path: str, min_silence_duration_ms: int) -> list:
        """Fallback silence detection using audio energy"""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_wav(audio_path)
            silence_segments = []
            
            # Detect silence (threshold in dB, min_silence_len in ms)
            chunks = audio[::100]  # Check every 100ms
            in_silence = False
            silence_start = None
            
            for i, chunk in enumerate(chunks):
                if chunk.dBFS < -40:  # Silence threshold
                    if not in_silence:
                        in_silence = True
                        silence_start = i * 100
                else:
                    if in_silence:
                        silence_duration = (i * 100) - silence_start
                        if silence_duration >= min_silence_duration_ms:
                            silence_segments.append((silence_start / 1000.0, (i * 100) / 1000.0))
                        in_silence = False
            
            return silence_segments
        except Exception as e:
            logger.error(f"Fallback silence detection failed: {e}")
            return []
    
    def detect_scenes(self, video_path: str, threshold: float = 30.0) -> list:
        """
        Detect scene changes in video.
        Returns: [timestamp_seconds, ...]
        """
        try:
            # Use new API (non-deprecated)
            scene_list = detect(video_path, ContentDetector(threshold=threshold))
            timestamps = [scene[0].get_seconds() for scene in scene_list]
            
            logger.info(f"Detected {len(timestamps)} scene changes")
            return timestamps
            
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            # Try fallback with old API if new one fails
            if VideoManager is not None and SceneManager is not None:
                try:
                    video_manager = VideoManager([video_path])
                    scene_manager = SceneManager()
                    scene_manager.add_detector(ContentDetector(threshold=threshold))
                    video_manager.set_duration()
                    video_manager.start()
                    scene_manager.detect_scenes(frame_source=video_manager)
                    scene_list = scene_manager.get_scene_list()
                    timestamps = [scene[0].get_seconds() for scene in scene_list]
                    logger.info(f"Detected {len(timestamps)} scene changes (using fallback API)")
                    return timestamps
                except Exception as e2:
                    logger.error(f"Scene detection fallback also failed: {e2}")
            return []
    
    def analyze_video(self, video_id: str, video_path: str, audio_path: str) -> dict:
        """
        Run complete analysis: silence + scene detection.
        Returns: {silence_segments: [...], scene_timestamps: [...]}
        """
        logger.info(f"Starting analysis for video {video_id}")
        
        # Detect silence
        silence_segments = self.detect_silence(audio_path)
        
        # Detect scenes
        scene_timestamps = self.detect_scenes(video_path)
        
        result = {
            "silence_segments": silence_segments,
            "scene_timestamps": scene_timestamps
        }
        
        logger.info(f"Analysis complete: {len(silence_segments)} silence segments, {len(scene_timestamps)} scene changes")
        return result

