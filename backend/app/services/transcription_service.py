from faster_whisper import WhisperModel
from app.database import SessionLocal
from app.models.video import Video
from app.models.transcript import Transcript
from app.config import get_settings
from pathlib import Path
import ffmpeg
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class TranscriptionService:
    def __init__(self):
        # Use "base" model for speed, "small" for better accuracy
        # Options: tiny, base, small, medium, large
        # For hackathon: "base" is good balance of speed/accuracy
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("TranscriptionService initialized with Whisper base model")
    
    def transcribe_video(self, video_id: str) -> dict:
        """
        Transcribe video and save to database.
        Returns: {segments: [...], language: str}
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            # Check if transcript already exists
            existing = db.query(Transcript).filter(Transcript.video_id == video_id).first()
            if existing:
                logger.info(f"Transcript already exists for {video_id}")
                return {
                    "segments": existing.segments,
                    "language": existing.language
                }
            
            # Extract audio if needed
            audio_path = self._extract_audio(video.original_path, video_id)
            
            # Transcribe
            logger.info(f"Transcribing {video_id}...")
            segments, info = self.model.transcribe(
                str(audio_path),
                beam_size=5,
                word_timestamps=True,
                language="en"  # Auto-detect if None, but "en" is faster
            )
            
            # Convert to list format
            transcript_segments = []
            for segment in segments:
                words = []
                for word in segment.words:
                    words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })
                
                transcript_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, 'avg_logprob', None),
                    "words": words
                })
            
            # Save to database
            # Handle different versions of faster-whisper
            confidence_data = {}
            if hasattr(info, 'avg_logprob'):
                confidence_data["avg_logprob"] = info.avg_logprob
            if hasattr(info, 'language_probability'):
                confidence_data["language_probability"] = info.language_probability
            
            transcript = Transcript(
                video_id=video_id,
                segments=transcript_segments,
                language=info.language,
                confidence=confidence_data if confidence_data else None
            )
            db.add(transcript)
            db.commit()
            
            logger.info(f"Transcription complete for {video_id}: {len(transcript_segments)} segments")
            
            return {
                "segments": transcript_segments,
                "language": info.language
            }
            
        except Exception as e:
            logger.error(f"Transcription failed for {video_id}: {e}")
            raise
        finally:
            db.close()
    
    def _extract_audio(self, video_path: str, video_id: str) -> Path:
        """Extract audio to WAV file for transcription"""
        output_dir = settings.TEMP_DIR / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / "audio.wav"
        
        # Return existing file if it exists
        if audio_path.exists():
            logger.info(f"Using existing audio file: {audio_path}")
            return audio_path
        
        try:
            logger.info(f"Extracting audio from {video_path} to {audio_path}")
            (
                ffmpeg
                .input(video_path)
                .output(
                    str(audio_path),
                    acodec='pcm_s16le',  # 16-bit PCM
                    ac=1,  # Mono channel
                    ar='16000'  # 16kHz sample rate (Whisper's preferred)
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            logger.info(f"Audio extracted successfully: {audio_path}")
            return audio_path
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Audio extraction failed: {error_msg}")
            raise Exception(f"Audio extraction failed: {error_msg}")

