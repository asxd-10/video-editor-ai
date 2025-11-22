from app.models.transcript import Transcript
from app.models.clip_candidate import ClipCandidate
from app.models.video import Video
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

class ClipSelector:
    def __init__(self):
        pass
    
    def generate_candidates(
        self, 
        video_id: str, 
        db, 
        min_duration: float = 15.0, 
        max_duration: float = 60.0,
        num_candidates: int = 5
    ) -> list:
        """
        Generate clip candidates with retention scores.
        Returns: List of ClipCandidate objects
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        if not transcript:
            raise ValueError("Transcript not found. Transcribe video first.")
        
        # Get analysis data
        silence_segments = []
        scene_timestamps = []
        if video.analysis_metadata:
            silence_segments = video.analysis_metadata.get("silence_segments", [])
            scene_timestamps = video.analysis_metadata.get("scene_timestamps", [])
        
        # Generate candidates using multiple strategies
        candidates = []
        
        # Strategy 1: High speech density segments
        density_candidates = self._find_high_density_segments(transcript, min_duration, max_duration)
        logger.info(f"Found {len(density_candidates)} high-density candidates")
        candidates.extend(density_candidates)
        
        # Strategy 2: Segments with keywords/hooks
        keyword_candidates = self._find_keyword_segments(transcript, min_duration, max_duration)
        logger.info(f"Found {len(keyword_candidates)} keyword-based candidates")
        candidates.extend(keyword_candidates)
        
        # Strategy 3: Segments around scene changes
        if scene_timestamps:
            scene_candidates = self._find_scene_based_segments(
                scene_timestamps, 
                video.duration_seconds or 0, 
                min_duration, 
                max_duration
            )
            logger.info(f"Found {len(scene_candidates)} scene-based candidates")
            candidates.extend(scene_candidates)
        
        # Strategy 4: If we have few candidates, use any transcript segments
        if len(candidates) < 3:
            logger.info("Few candidates found, adding transcript segments")
            for segment in transcript.segments:
                duration = segment["end"] - segment["start"]
                if min_duration <= duration <= max_duration:
                    candidates.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "features": {
                            "strategy": "transcript_segment",
                            "word_count": len(segment.get("words", []))
                        },
                        "hook_text": segment["text"][:100].strip()
                    })
        
        # Remove duplicates and score candidates
        unique_candidates = self._deduplicate_candidates(candidates)
        scored_candidates = []
        
        for candidate in unique_candidates:
            score = self._calculate_retention_score(
                candidate, 
                transcript, 
                silence_segments,
                video.duration_seconds or 0
            )
            scored_candidates.append({
                **candidate,
                "score": score
            })
        
        # Sort by score and take top N
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = scored_candidates[:num_candidates]
        
        # Save to database
        clip_objects = []
        for cand in top_candidates:
            clip = ClipCandidate(
                video_id=video_id,
                start_time=cand["start"],
                end_time=cand["end"],
                duration=cand["end"] - cand["start"],
                score=cand["score"],
                features=cand.get("features", {}),
                hook_text=cand.get("hook_text"),
                hook_timestamp=cand.get("hook_timestamp", cand["start"])
            )
            db.add(clip)
            clip_objects.append(clip)
        
        db.commit()
        logger.info(f"Generated {len(clip_objects)} clip candidates for {video_id}")
        return clip_objects
    
    def _find_high_density_segments(self, transcript, min_duration, max_duration):
        """Find segments with high speech density"""
        candidates = []
        
        for segment in transcript.segments:
            duration = segment["end"] - segment["start"]
            if min_duration <= duration <= max_duration:
                word_count = len(segment.get("words", []))
                speech_density = word_count / duration if duration > 0 else 0
                
                if speech_density > 2.0:  # > 2 words per second
                    candidates.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "features": {
                            "speech_density": speech_density,
                            "word_count": word_count,
                            "strategy": "high_density"
                        }
                    })
        
        return candidates
    
    def _find_keyword_segments(self, transcript, min_duration, max_duration):
        """Find segments with engaging keywords"""
        keywords = [
            "amazing", "incredible", "watch", "check", "here", "now", 
            "you", "this", "that", "important", "key", "secret", 
            "learn", "discover", "reveal", "surprising"
        ]
        candidates = []
        
        for segment in transcript.segments:
            text_lower = segment["text"].lower()
            keyword_count = sum(1 for kw in keywords if kw in text_lower)
            
            if keyword_count > 0:
                duration = segment["end"] - segment["start"]
                if min_duration <= duration <= max_duration:
                    # Extract hook (first 100 chars)
                    hook_text = segment["text"][:100].strip()
                    candidates.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "features": {
                            "keyword_count": keyword_count,
                            "strategy": "keywords"
                        },
                        "hook_text": hook_text,
                        "hook_timestamp": segment["start"]
                    })
        
        return candidates
    
    def _find_scene_based_segments(self, scene_timestamps, video_duration, min_duration, max_duration):
        """Find segments around scene changes"""
        candidates = []
        
        for i, scene_time in enumerate(scene_timestamps):
            if i + 1 < len(scene_timestamps):
                start = scene_time
                end = scene_timestamps[i + 1]
                duration = end - start
                
                if min_duration <= duration <= max_duration:
                    candidates.append({
                        "start": start,
                        "end": end,
                        "features": {
                            "scene_based": True,
                            "strategy": "scene_change"
                        }
                    })
        
        return candidates
    
    def _deduplicate_candidates(self, candidates):
        """Remove duplicate or overlapping candidates"""
        if not candidates:
            return []
        
        # Sort by start time
        sorted_candidates = sorted(candidates, key=lambda x: x["start"])
        unique = [sorted_candidates[0]]
        
        for cand in sorted_candidates[1:]:
            # Check if overlaps significantly with last candidate
            last = unique[-1]
            overlap = min(cand["end"], last["end"]) - max(cand["start"], last["start"])
            overlap_ratio = overlap / min(cand["end"] - cand["start"], last["end"] - last["start"])
            
            # Only add if overlap is < 50%
            if overlap_ratio < 0.5:
                unique.append(cand)
        
        return unique
    
    def _calculate_retention_score(self, candidate, transcript, silence_segments, video_duration):
        """Calculate retention score (0-100)"""
        score = 50  # Base score
        
        start, end = candidate["start"], candidate["end"]
        duration = end - start
        
        # Speech density bonus
        speech_density = candidate.get("features", {}).get("speech_density", 0)
        if speech_density > 0:
            score += min(speech_density * 10, 20)  # Max +20
        
        # Keyword bonus
        keyword_count = candidate.get("features", {}).get("keyword_count", 0)
        score += min(keyword_count * 5, 15)  # Max +15
        
        # Silence penalty
        silence_in_segment = sum(
            max(0, min(silence_end, end) - max(silence_start, start))
            for silence_start, silence_end in silence_segments
        )
        silence_ratio = silence_in_segment / duration if duration > 0 else 0
        score -= silence_ratio * 30  # Penalty up to -30
        
        # Duration bonus (prefer 20-40s)
        if 20 <= duration <= 40:
            score += 10
        elif duration < 15 or duration > 60:
            score -= 10
        
        # Position bonus (earlier is better for hooks)
        if start < video_duration * 0.1:  # First 10% of video
            score += 5
        
        return max(0, min(100, score))

