"""
Core video editing service.
Handles silence removal, jump cuts, captions, audio normalization, and rendering.
"""
import ffmpeg
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.database import SessionLocal
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class EditorService:
    """Service for applying video edits and rendering final output"""
    
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def create_edit(
        self,
        video_id: str,
        clip_candidate_id: Optional[str] = None,
        edit_options: Dict = None
    ) -> Dict:
        """
        Create an edited video based on clip candidate and edit options.
        
        Args:
            video_id: Video to edit
            clip_candidate_id: Optional clip candidate to use (if None, uses full video)
            edit_options: {
                remove_silence: bool,
                jump_cuts: bool,
                dynamic_zoom: bool,
                captions: bool,
                caption_style: str,  # "burn_in" or "srt"
                pace_optimize: bool,
                aspect_ratios: List[str]  # ["9:16", "1:1", "16:9"]
            }
        
        Returns:
            Dict with output paths for each aspect ratio
        """
        db = SessionLocal()
        try:
            # Load video and related data
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            # Get clip candidate if specified
            clip_start = 0.0
            clip_end = video.duration_seconds or 0.0
            
            if clip_candidate_id:
                clip = db.query(ClipCandidate).filter(
                    ClipCandidate.id == clip_candidate_id
                ).first()
                if clip:
                    clip_start = clip.start_time
                    clip_end = clip.end_time
            
            # Get transcript for word-level editing (optional - editing works without it)
            transcript = db.query(Transcript).filter(
                Transcript.video_id == video_id
            ).first()
            
            # Get analysis metadata (silence segments) - optional
            # Convert from tuples to dicts if needed: [(start, end), ...] -> [{"start": ..., "end": ...}, ...]
            silence_segments = []
            if video.analysis_metadata:
                raw_silences = video.analysis_metadata.get("silence_segments", [])
                for silence in raw_silences:
                    if isinstance(silence, (list, tuple)) and len(silence) == 2:
                        # Convert tuple/list to dict
                        silence_segments.append({"start": silence[0], "end": silence[1]})
                    elif isinstance(silence, dict) and "start" in silence and "end" in silence:
                        # Already in dict format
                        silence_segments.append(silence)
                logger.info(f"Loaded {len(silence_segments)} silence segments for editing")
            
            # If transcript is required for certain edits but doesn't exist, adjust options
            if not transcript:
                # Disable transcript-dependent features
                if edit_options.get("jump_cuts"):
                    logger.warning("Jump cuts disabled: transcript not available")
                    edit_options["jump_cuts"] = False
                if edit_options.get("captions"):
                    logger.warning("Captions disabled: transcript not available")
                    edit_options["captions"] = False
            
            # Default edit options
            if edit_options is None:
                edit_options = {
                    "remove_silence": True,
                    "jump_cuts": True,
                    "dynamic_zoom": False,
                    "captions": True,
                    "caption_style": "burn_in",
                    "pace_optimize": False,
                    "aspect_ratios": ["16:9"]  # Default to original aspect ratio
                }
            
            # Build edit decision list (EDL)
            edl = self._build_edit_decision_list(
                clip_start, clip_end, transcript, silence_segments, edit_options
            )
            
            # Check if video has audio (for audio normalization)
            has_audio = getattr(video, 'has_audio', True)
            
            # Render video for each aspect ratio
            output_paths = {}
            for aspect_ratio in edit_options.get("aspect_ratios", ["16:9"]):
                output_path = self._render_video(
                    video.original_path,
                    edl,
                    aspect_ratio,
                    transcript if edit_options.get("captions") else None,
                    edit_options,
                    video_id,
                    aspect_ratio,
                    has_audio
                )
                output_paths[aspect_ratio] = output_path
            
            return {
                "output_paths": output_paths,
                "edl": edl,
                "clip_used": {
                    "start": clip_start,
                    "end": clip_end,
                    "duration": clip_end - clip_start
                }
            }
            
        finally:
            db.close()
    
    def _build_edit_decision_list(
        self,
        start_time: float,
        end_time: float,
        transcript: Optional[Transcript],
        silence_segments: List[Dict],
        edit_options: Dict
    ) -> List[Dict]:
        """
        Build Edit Decision List (EDL) - list of segments to keep.
        
        Returns:
            List of {start, end, type} segments
        """
        edl = []
        
        # If no transcript, we can still do silence removal if silence segments exist
        if not transcript or not transcript.segments:
            # Can still remove silence without transcript
            if edit_options.get("remove_silence") and silence_segments:
                # Remove silence segments directly (no transcript needed)
                clip_silences = [
                    s for s in silence_segments
                    if s["end"] >= start_time and s["start"] <= end_time
                ]
                
                if clip_silences:
                    # Build EDL by keeping everything except silence
                    current_time = start_time
                    for silence in sorted(clip_silences, key=lambda x: x["start"]):
                        # Add segment before silence
                        if silence["start"] > current_time:
                            edl.append({
                                "start": current_time,
                                "end": silence["start"],
                                "type": "keep"
                            })
                        current_time = max(current_time, silence["end"])
                    
                    # Add final segment after last silence
                    if current_time < end_time:
                        edl.append({
                            "start": current_time,
                            "end": end_time,
                            "type": "keep"
                        })
                    
                    # If no segments added (all silence), keep a small portion
                    if not edl:
                        edl.append({
                            "start": start_time,
                            "end": min(start_time + 1.0, end_time),  # Keep 1 second
                            "type": "keep"
                        })
                    
                    logger.info(f"Removed {len(clip_silences)} silence segments (no transcript)")
                    return edl
            else:
                # No transcript and no silence removal - just return clip range
                edl.append({
                    "start": start_time,
                    "end": end_time,
                    "type": "keep"
                })
                return edl
        
        # Filter transcript segments within clip range
        relevant_segments = [
            seg for seg in transcript.segments
            if seg["end"] >= start_time and seg["start"] <= end_time
        ]
        
        if not relevant_segments:
            edl.append({"start": start_time, "end": end_time, "type": "keep"})
            return edl
        
        # Strategy 1: Remove silence (if enabled)
        if edit_options.get("remove_silence") and silence_segments:
            # Filter silence segments within clip range
            clip_silences = [
                s for s in silence_segments
                if s["end"] >= start_time and s["start"] <= end_time
            ]
            
            # Simple approach: keep all transcript segments, skip silence gaps
            current_time = start_time
            for seg in relevant_segments:
                seg_start = max(seg["start"], current_time, start_time)
                seg_end = min(seg["end"], end_time)
                
                # Skip if this segment is entirely within a silence
                is_silence = False
                for silence in clip_silences:
                    if seg_start >= silence["start"] and seg_end <= silence["end"]:
                        is_silence = True
                        break
                
                if not is_silence and seg_end > seg_start:
                    edl.append({
                        "start": seg_start,
                        "end": seg_end,
                        "type": "keep"
                    })
                    current_time = seg_end
            
            # If no segments added, keep the whole clip
            if not edl:
                edl.append({
                    "start": start_time,
                    "end": end_time,
                    "type": "keep"
                })
        elif edit_options.get("jump_cuts") and transcript:
            # Strategy 2: Jump cuts at word boundaries
            # Use word-level timestamps for precise cuts
            words = []
            for seg in relevant_segments:
                if "words" in seg:
                    words.extend([
                        w for w in seg["words"]
                        if w["start"] >= start_time and w["end"] <= end_time
                    ])
            
            # Group words into phrases (remove gaps > 0.5s)
            if words:
                current_phrase_start = words[0]["start"]
                current_phrase_end = words[0]["end"]
                
                for i in range(1, len(words)):
                    gap = words[i]["start"] - current_phrase_end
                    if gap > 0.5:  # Gap too large, start new segment
                        edl.append({
                            "start": current_phrase_start,
                            "end": current_phrase_end,
                            "type": "keep"
                        })
                        current_phrase_start = words[i]["start"]
                    current_phrase_end = words[i]["end"]
                
                # Add final phrase
                edl.append({
                    "start": current_phrase_start,
                    "end": min(current_phrase_end, end_time),
                    "type": "keep"
                })
            else:
                # Fallback: use segment boundaries
                for seg in relevant_segments:
                    edl.append({
                        "start": max(seg["start"], start_time),
                        "end": min(seg["end"], end_time),
                        "type": "keep"
                    })
        else:
            # No editing, just keep the clip
            edl.append({
                "start": start_time,
                "end": end_time,
                "type": "keep"
            })
        
        # Merge adjacent segments
        merged_edl = []
        for segment in sorted(edl, key=lambda x: x["start"]):
            if merged_edl and merged_edl[-1]["end"] >= segment["start"]:
                # Merge with previous
                merged_edl[-1]["end"] = max(merged_edl[-1]["end"], segment["end"])
            else:
                merged_edl.append(segment)
        
        return merged_edl
    
    def _render_video(
        self,
        input_path: str,
        edl: List[Dict],
        aspect_ratio: str,
        transcript: Optional[Transcript],
        edit_options: Dict,
        video_id: str,
        aspect_label: str,
        has_audio: bool = True
    ) -> str:
        """
        Render final edited video using ffmpeg.
        
        Returns:
            Path to rendered video
        """
        output_dir = Path(settings.PROCESSED_DIR) / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"edited_{aspect_label.replace(':', '_')}.mp4"
        
        try:
            # Build ffmpeg filter complex for concatenation
            # Strategy: Use concat demuxer (faster than filter_complex)
            
            # Create temporary segment files
            segment_files = []
            temp_segments_dir = self.temp_dir / f"{video_id}_{aspect_label}"
            temp_segments_dir.mkdir(parents=True, exist_ok=True)
            
            for i, segment in enumerate(edl):
                seg_path = temp_segments_dir / f"seg_{i:04d}.mp4"
                
                # Extract segment
                input_stream = ffmpeg.input(input_path, ss=segment["start"])
                output_stream = input_stream
                
                # Calculate duration
                duration = segment["end"] - segment["start"]
                
                # Apply aspect ratio conversion if needed
                if aspect_ratio != "16:9":
                    output_stream = self._apply_aspect_ratio(output_stream, aspect_ratio)
                
                # Note: Dynamic zoom and pace optimization are complex
                # For MVP, we'll skip these for now to ensure stability
                # TODO: Implement dynamic zoom with face detection
                # TODO: Implement pace optimization based on segment analysis
                
                # Output segment
                (
                    ffmpeg
                    .output(
                        output_stream,
                        str(seg_path),
                        t=duration,
                        vcodec='libx264',
                        acodec='aac',
                        preset='medium',
                        crf=23
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                segment_files.append(seg_path)
            
            # Concatenate segments
            concat_file = temp_segments_dir / "concat.txt"
            with open(concat_file, 'w') as f:
                for seg_file in segment_files:
                    f.write(f"file '{seg_file.absolute()}'\n")
            
            # Check if segments have audio by probing first segment
            has_audio_in_segments = False
            if has_audio and segment_files:
                try:
                    probe = ffmpeg.probe(str(segment_files[0]))
                    has_audio_in_segments = any(
                        s.get('codec_type') == 'audio' 
                        for s in probe.get('streams', [])
                    )
                except Exception as e:
                    logger.warning(f"Could not probe segment for audio: {e}")
                    has_audio_in_segments = False
            
            # Concatenate and add captions
            input_concat = ffmpeg.input(str(concat_file), format='concat', safe=0)
            
            # Split video and audio streams
            video_stream = input_concat['v']
            
            # Add captions to video if enabled
            if edit_options.get("captions") and transcript:
                video_stream = self._add_captions(
                    video_stream, transcript, edit_options.get("caption_style", "burn_in")
                )
            
            # Handle audio if it exists
            if has_audio_in_segments:
                try:
                    audio_stream = input_concat['a']
                    # Normalize audio
                    audio_stream = self._normalize_audio(audio_stream)
                    
                    # Final render with audio
                    (
                        ffmpeg
                        .output(
                            video_stream,
                            audio_stream,
                            str(output_path),
                            vcodec='libx264',
                            acodec='aac',
                            preset='medium',
                            crf=23,
                            movflags='faststart'
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                except (KeyError, AttributeError, Exception) as e:
                    logger.warning(f"Audio processing failed: {e}, rendering video only")
                    # Fallback to video only
                    (
                        ffmpeg
                        .output(
                            video_stream,
                            str(output_path),
                            vcodec='libx264',
                            preset='medium',
                            crf=23,
                            movflags='faststart'
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
            else:
                # Video only (no audio)
                logger.info(f"Rendering video only (no audio) for {video_id}")
                (
                    ffmpeg
                    .output(
                        video_stream,
                        str(output_path),
                        vcodec='libx264',
                        preset='medium',
                        crf=23,
                        movflags='faststart'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            
            logger.info(f"Rendered video: {output_path}")
            return str(output_path)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Rendering failed: {error_msg}")
            raise Exception(f"Rendering failed: {error_msg}")
    
    def _apply_aspect_ratio(self, stream, aspect_ratio: str) -> ffmpeg.Stream:
        """Apply aspect ratio conversion (crop/scale with smart centering)"""
        # Parse aspect ratio
        if aspect_ratio == "9:16":
            # Vertical (TikTok/Reels) - 1080x1920
            # Scale to fit height, then crop width
            return stream.filter('scale', -1, 1920).filter('crop', 1080, 1920, '(iw-1080)/2', 0)
        elif aspect_ratio == "1:1":
            # Square (Instagram) - 1080x1080
            # Scale to fit width, then crop height
            return stream.filter('scale', 1080, -1).filter('crop', 1080, 1080, 0, '(ih-1080)/2')
        elif aspect_ratio == "16:9":
            # Horizontal (YouTube) - 1920x1080
            # Scale to fit width, then crop height
            return stream.filter('scale', 1920, -1).filter('crop', 1920, 1080, 0, '(ih-1080)/2')
        else:
            return stream
    
    def _apply_dynamic_zoom(self, stream, segment: Dict) -> ffmpeg.Stream:
        """Apply dynamic zoom effect (placeholder - would use face detection)"""
        # For now, simple zoom in/out
        # TODO: Use mediapipe for face detection and center zoom
        return stream.filter('zoompan', z='1.1', d=25, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)')
    
    def _apply_pace_optimization(self, stream, segment: Dict) -> ffmpeg.Stream:
        """Apply pace optimization (speed adjustment)"""
        # Slight speed increase for slow segments
        # TODO: Analyze segment pace and adjust accordingly
        return stream.filter('setpts', '0.95*PTS')
    
    def _add_captions(
        self,
        stream: ffmpeg.Stream,
        transcript: Transcript,
        style: str
    ) -> ffmpeg.Stream:
        """Add captions to video"""
        if style == "burn_in":
            # Generate SRT file for subtitles
            srt_path = self.temp_dir / f"captions_{transcript.video_id}.srt"
            self._generate_srt(transcript, srt_path)
            
            # Burn in subtitles using ffmpeg subtitles filter
            return stream.filter(
                'subtitles',
                str(srt_path),
                force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'
            )
        else:
            # Return SRT file path for external use
            return stream
    
    def _generate_srt(self, transcript: Transcript, output_path: Path):
        """Generate SRT subtitle file from transcript"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcript.segments, 1):
                start_time = self._format_srt_time(segment["start"])
                end_time = self._format_srt_time(segment["end"])
                text = segment["text"].strip()
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _normalize_audio(self, audio_stream: ffmpeg.Stream) -> ffmpeg.Stream:
        """Normalize audio using loudnorm filter"""
        # Use loudnorm for broadcast-standard audio normalization (-16 LUFS)
        # Apply filter to audio stream specifically
        return audio_stream.filter('loudnorm', I=-16, TP=-1.5, LRA=11)

