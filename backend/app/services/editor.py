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
from app.models.media import Media  # Use Media instead of Video
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
    
    def render_from_edl(
        self,
        video_id: str,
        edl: List[Dict],
        edit_options: Dict = None,
        media_data: Dict = None  # Cached media data to avoid DB query
    ) -> Dict:
        """
        Render video directly from provided EDL (for AI edits).
        
        Args:
            video_id: Video ID to edit
            edl: Edit Decision List [{"start": float, "end": float, "type": "keep"}]
            edit_options: {
                captions: bool,
                caption_style: str,  # "burn_in" or "srt"
                aspect_ratios: List[str]  # ["9:16", "1:1", "16:9"]
            }
            media_data: Optional cached media data {
                video_url: str,
                original_path: str,
                duration_seconds: float,
                has_audio: bool,
                transcript_segments: List[Dict]  # Optional, for captions
            }
        
        Returns:
            Dict with output paths for each aspect ratio
        """
        # Use cached media_data if provided, otherwise query database
        cached_video_path = None  # Initialize
        db = None
        try:
            if media_data:
                video_url = media_data.get("video_url")
                original_path = media_data.get("original_path")
                cached_video_path = media_data.get("cached_video_path")  # Locally cached file
                video_duration = media_data.get("duration_seconds", 0.0)
                has_audio = media_data.get("has_audio", True)
                transcript_segments = media_data.get("transcript_segments")
                # No DB session needed when using cached data
            else:
                # Fallback: query database (may timeout in Celery tasks)
                db = SessionLocal()
                # Load media record
                media = db.query(Media).filter(Media.video_id == video_id).first()
                if not media:
                    raise ValueError(f"Video {video_id} not found")
                
                video_url = getattr(media, 'video_url', None)
                original_path = getattr(media, 'original_path', None)
                video_duration = media.duration_seconds or 0.0
                has_audio = getattr(media, 'has_audio', True) if hasattr(media, 'has_audio') else True
                transcript_segments = None
            
            # Validate EDL
            if not edl or len(edl) == 0:
                raise ValueError("EDL cannot be empty")
            
            # Validate EDL segments are within video duration
            for segment in edl:
                if segment.get("start", 0) < 0 or segment.get("end", 0) > video_duration:
                    logger.warning(f"Segment {segment} is outside video duration ({video_duration}s)")
                if segment.get("start", 0) >= segment.get("end", 0):
                    raise ValueError(f"Invalid segment: start >= end in {segment}")
            
            # Get transcript if captions are enabled
            transcript = None
            if edit_options and edit_options.get("captions"):
                if transcript_segments:
                    # Use cached transcript segments
                    from app.models.transcript import Transcript
                    # Create a mock transcript object with segments
                    class MockTranscript:
                        def __init__(self, segments, video_id):
                            self.segments = segments
                            self.video_id = video_id
                    transcript = MockTranscript(transcript_segments, video_id)
                elif db:
                    # Query database for transcript
                    transcript = db.query(Transcript).filter(
                        Transcript.video_id == video_id
                    ).first()
                    if not transcript:
                        logger.warning("Captions requested but transcript not found, disabling captions")
                        edit_options["captions"] = False
                else:
                    logger.warning("Captions requested but no transcript data available, disabling captions")
                    edit_options["captions"] = False
            
            # Default edit options
            if edit_options is None:
                edit_options = {
                    "captions": False,
                    "caption_style": "burn_in",
                    "aspect_ratios": ["16:9"]
                }
            
            # Determine input path: prioritize cached local file, then video_url, then original_path
            video_input_path = None
            fallback_path = None
            
            # First, check if we have a cached local file (downloaded at start)
            if cached_video_path:
                from pathlib import Path
                cached_path = Path(cached_video_path)
                if cached_path.exists():
                    video_input_path = str(cached_path)
                    logger.info(f"Using cached local video file: {video_input_path}")
                else:
                    logger.warning(f"Cached video path does not exist: {cached_video_path}, falling back to URL")
            
            # If no cached file, use video_url or original_path
            if not video_input_path:
                if video_url and video_url.strip():
                    video_input_path = video_url.strip()
                    logger.info(f"Using video_url (S3/URL): {video_input_path[:80]}...")
                    
                    # Set fallback to original_path if it's a local file (not a URL)
                    if original_path and original_path.strip():
                        original_path_clean = original_path.strip()
                        if not (original_path_clean.startswith('http://') or original_path_clean.startswith('https://')):
                            # Check if local file exists
                            from pathlib import Path
                            path_obj = Path(original_path_clean)
                            if path_obj.exists():
                                fallback_path = original_path_clean
                            else:
                                from app.config import get_settings
                                settings = get_settings()
                                abs_path = Path(settings.BASE_STORAGE_PATH) / original_path_clean.lstrip('/')
                                if abs_path.exists():
                                    fallback_path = str(abs_path)
                elif original_path and original_path.strip():
                    original_path_clean = original_path.strip()
                    # Check if it's a URL or local path
                    if original_path_clean.startswith('http://') or original_path_clean.startswith('https://'):
                        video_input_path = original_path_clean
                        logger.info(f"Using original_path (URL): {video_input_path[:80]}...")
                    else:
                        # Local path - check if file exists
                        from pathlib import Path
                        path_obj = Path(original_path_clean)
                        if not path_obj.exists():
                            # Try relative to storage base
                            from app.config import get_settings
                            settings = get_settings()
                            abs_path = Path(settings.BASE_STORAGE_PATH) / original_path_clean.lstrip('/')
                            if abs_path.exists():
                                video_input_path = str(abs_path)
                                logger.info(f"Using original_path (local, resolved): {video_input_path}")
                            else:
                                raise ValueError(
                                    f"Video file not found for video {video_id}. "
                                    f"Tried: {original_path_clean} and {abs_path}. "
                                    f"Please ensure video_url is set in media table or file exists at original_path."
                                )
                        else:
                            video_input_path = original_path_clean
                            logger.info(f"Using original_path (local): {video_input_path}")
                
                if not video_input_path:
                    raise ValueError(
                        f"No video source found for video {video_id}. "
                        f"Please set video_url (S3 URL) or original_path in media table."
                    )
            
            # Render video for each aspect ratio
            output_paths = {}
            for aspect_ratio in edit_options.get("aspect_ratios", ["16:9"]):
                # Use cached local file (if downloaded) or URL/local path
                try:
                    output_path = self._render_video(
                        video_input_path,  # Can be cached local file, S3 URL, or local path
                        edl,
                        aspect_ratio,
                        transcript if edit_options.get("captions") else None,
                        edit_options,
                        video_id,
                        aspect_ratio,
                        has_audio
                    )
                    output_paths[aspect_ratio] = output_path
                except Exception as e:
                    # If rendering fails and we have a fallback local path, try that
                    if fallback_path and video_input_path != fallback_path:
                        logger.warning(
                            f"Failed to render from video source ({video_input_path[:80] if len(str(video_input_path)) > 80 else video_input_path}...), "
                            f"trying fallback local path: {fallback_path}"
                        )
                        try:
                            output_path = self._render_video(
                                fallback_path,
                                edl,
                                aspect_ratio,
                                transcript if edit_options.get("captions") else None,
                                edit_options,
                                video_id,
                                aspect_ratio,
                                has_audio
                            )
                            output_paths[aspect_ratio] = output_path
                        except Exception as fallback_error:
                            raise Exception(
                                f"Render error: Failed to render from both S3 URL and local path. "
                                f"S3 URL error: {str(e)[:200]}. "
                                f"Local path error: {str(fallback_error)[:200]}"
                            )
                    else:
                        raise Exception(
                            f"Render error: Failed to render video. "
                            f"Source: {video_input_path[:100] if len(str(video_input_path)) > 100 else video_input_path}. "
                            f"Error: {str(e)[:500]}"
                        )
            
            return {
                "output_paths": output_paths,
                "edl": edl,
                "total_duration": sum(seg["end"] - seg["start"] for seg in edl)
            }
        finally:
            if db:
                db.close()
    
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
            # Load media record (using unified schema)
            media = db.query(Media).filter(Media.video_id == video_id).first()
            if not media:
                raise ValueError(f"Video {video_id} not found")
            
            # Get clip candidate if specified
            clip_start = 0.0
            clip_end = media.duration_seconds or 0.0
            
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
            if media.analysis_metadata:
                raw_silences = media.analysis_metadata.get("silence_segments", [])
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
            
            # Check if media has audio (for audio normalization)
            has_audio = getattr(media, 'has_audio', True) if hasattr(media, 'has_audio') else True
            
            # Render video for each aspect ratio
            output_paths = {}
            for aspect_ratio in edit_options.get("aspect_ratios", ["16:9"]):
                output_path = self._render_video(
                    media.original_path,  # Use media.original_path instead of video.original_path
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
            
            valid_segments = []
            for i, segment in enumerate(edl):
                # Calculate duration
                duration = segment["end"] - segment["start"]
                
                # Skip segments that are too small (< 0.1 seconds) or invalid
                if duration < 0.1:
                    logger.warning(f"Skipping segment {i}: duration too small ({duration:.3f}s)")
                    continue
                
                valid_segments.append((i, segment))
            
            # Check if we have any valid segments
            if not valid_segments:
                raise ValueError("No valid segments in EDL (all segments were too small or invalid)")
            
            for seg_idx, segment in valid_segments:
                seg_path = temp_segments_dir / f"seg_{seg_idx:04d}.mp4"
                
                # Extract segment
                # FFmpeg can handle URLs directly (including S3 URLs)
                # Note: Some FFmpeg builds don't support http_persistent, so we don't use it
                input_kwargs = {"ss": segment["start"]}
                
                # For remote URLs, FFmpeg handles them natively without special options
                input_stream = ffmpeg.input(input_path, **input_kwargs)
                output_stream = input_stream
                
                # Apply aspect ratio conversion if needed
                # Note: For 16:9, we keep original (or scale to standard 1920x1080)
                # For other ratios, apply conversion
                if aspect_ratio != "16:9":
                    output_stream = self._apply_aspect_ratio(output_stream, aspect_ratio)
                else:
                    # For 16:9, optionally scale to standard resolution
                    # output_stream = output_stream.filter('scale', 1920, 1080)
                    pass  # Keep original resolution for now
                
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
            # Convert to relative path from BASE_STORAGE_PATH for URL generation
            try:
                # Ensure output_path is absolute
                if not output_path.is_absolute():
                    output_path = output_path.resolve()
                
                # Get relative path from BASE_STORAGE_PATH
                relative_path = output_path.relative_to(settings.BASE_STORAGE_PATH)
                # Return as URL path (will be converted to full URL in API)
                return f"/storage/{relative_path.as_posix()}"
            except ValueError as e:
                # If path is not relative to BASE_STORAGE_PATH, try to resolve it
                logger.warning(f"Could not get relative path for {output_path}: {e}")
                # Try to construct path manually
                if 'processed' in str(output_path):
                    # Extract video_id and filename from path
                    parts = Path(output_path).parts
                    if 'processed' in parts:
                        idx = parts.index('processed')
                        if idx + 1 < len(parts):
                            video_id = parts[idx + 1]
                            filename = parts[-1] if len(parts) > idx + 2 else None
                            if filename:
                                return f"/storage/processed/{video_id}/{filename}"
                # Fallback: return the path as is (API will handle conversion)
                return str(output_path)
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Rendering failed: {error_msg}")
            raise Exception(f"Rendering failed: {error_msg}")
    
    def _apply_aspect_ratio(self, stream, aspect_ratio: str) -> ffmpeg.Stream:
        """
        Apply aspect ratio conversion (crop/scale with smart centering).
        Uses scale then crop to ensure output fits within target dimensions.
        """
        if aspect_ratio == "9:16":
            # Vertical (TikTok/Reels) - 1080x1920
            # Strategy: Scale to fit height (1920), then crop width to 1080
            return stream.filter('scale', -1, 1920).filter('crop', 1080, 1920, '(iw-1080)/2', 0)
        elif aspect_ratio == "1:1":
            # Square (Instagram) - 1080x1080
            # Strategy: Scale to ensure BOTH dimensions are >= 1080, then crop to square
            # If width > height: scale width to 1080, height becomes >= 1080 (good)
            # If height > width: scale height to 1080, width becomes >= 1080 (good)
            # If width == height: scale both to 1080 (good)
            # This ensures we always have enough pixels to crop to 1080x1080
            return stream.filter(
                'scale', 
                'if(gt(iw,ih),1080,-1)',  # If width > height: scale width to 1080, height auto
                'if(gt(ih,iw),-1,1080)'   # If height > width: scale height to 1080, width auto
            ).filter('crop', 1080, 1080, '(iw-1080)/2', '(ih-1080)/2')
        elif aspect_ratio == "16:9":
            # Horizontal (YouTube) - 1920x1080
            # Strategy: Scale to fit width (1920), then crop height to 1080
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

