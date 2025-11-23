"""
EDL Validator Service
Validates LLM-generated Edit Decision Lists to prevent hallucinations and errors
"""
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class EDLValidator:
    """
    Validates and sanitizes LLM-generated EDLs.
    Prevents hallucinations, invalid timestamps, and logical errors.
    """
    
    def __init__(self, video_duration: float, tolerance: float = 0.1):
        """
        Args:
            video_duration: Total video duration in seconds
            tolerance: Allowed timestamp tolerance (seconds)
        """
        self.video_duration = video_duration
        self.tolerance = tolerance
    
    def validate_edl(self, edl: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[Dict]]:
        """
        Validate EDL from LLM.
        
        Args:
            edl: Edit Decision List from LLM
        
        Returns:
            (is_valid, errors, sanitized_edl)
        """
        errors = []
        sanitized = []
        
        if not isinstance(edl, list):
            return False, ["EDL must be a list"], []
        
        if len(edl) == 0:
            return False, ["EDL cannot be empty"], []
        
        # Sort by start time
        sorted_edl = sorted(edl, key=lambda x: x.get("start", 0))
        
        for i, segment in enumerate(sorted_edl):
            segment_errors = []
            
            # Validate required fields
            if "start" not in segment:
                segment_errors.append(f"Segment {i}: Missing 'start' timestamp")
                continue
            
            if "end" not in segment:
                segment_errors.append(f"Segment {i}: Missing 'end' timestamp")
                continue
            
            start = float(segment["start"])
            end = float(segment["end"])
            
            # Validate timestamp ranges
            if start < 0:
                segment_errors.append(f"Segment {i}: Start time {start} is negative")
                start = 0.0
            
            if end > self.video_duration:
                segment_errors.append(
                    f"Segment {i}: End time {end} exceeds video duration {self.video_duration}"
                )
                end = self.video_duration
            
            if start >= end:
                segment_errors.append(
                    f"Segment {i}: Start {start} >= End {end}"
                )
                continue  # Skip invalid segment
            
            # Validate segment duration (not too short or too long)
            duration = end - start
            if duration < 0.1:
                segment_errors.append(
                    f"Segment {i}: Duration {duration} too short (<0.1s)"
                )
                continue  # Skip too-short segments
            
            if duration > self.video_duration * 0.9:
                segment_errors.append(
                    f"Segment {i}: Duration {duration} suspiciously long"
                )
                # Allow but warn
            
            # Sanitize segment
            sanitized_segment = {
                "start": round(start, 2),
                "end": round(end, 2),
                "type": segment.get("type", "keep"),
                "reason": segment.get("reason", ""),
                "transition_type": segment.get("transition_type"),
                "transition_duration": segment.get("transition_duration")
            }
            
            # Remove None values
            sanitized_segment = {k: v for k, v in sanitized_segment.items() if v is not None}
            
            sanitized.append(sanitized_segment)
            
            if segment_errors:
                errors.extend(segment_errors)
        
        # Validate no overlapping segments (except transitions)
        overlap_errors = self._check_overlaps(sanitized)
        errors.extend(overlap_errors)
        
        # Validate coverage (segments should cover significant portion)
        coverage = self._calculate_coverage(sanitized)
        if coverage < 0.5:  # Less than 50% coverage
            errors.append(f"Warning: EDL only covers {coverage*100:.1f}% of video")
        
        is_valid = len(errors) == 0 or all("Warning" in e for e in errors)
        
        return is_valid, errors, sanitized
    
    def _check_overlaps(self, edl: List[Dict]) -> List[str]:
        """Check for overlapping segments (invalid)"""
        errors = []
        
        for i in range(len(edl) - 1):
            current = edl[i]
            next_seg = edl[i + 1]
            
            # Transitions can overlap, but regular segments shouldn't
            if current.get("type") != "transition" and next_seg.get("type") != "transition":
                if current["end"] > next_seg["start"] + self.tolerance:
                    errors.append(
                        f"Warning: Segments {i} and {i+1} overlap: "
                        f"{current['end']:.2f}s > {next_seg['start']:.2f}s"
                    )
        
        return errors
    
    def _calculate_coverage(self, edl: List[Dict]) -> float:
        """Calculate what percentage of video is covered by EDL"""
        if not edl:
            return 0.0
        
        total_covered = sum(
            seg["end"] - seg["start"]
            for seg in edl
            if seg.get("type") == "keep"
        )
        
        return total_covered / self.video_duration if self.video_duration > 0 else 0.0
    
    def validate_story_analysis(self, story_analysis: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate story analysis structure"""
        errors = []
        
        required_fields = ["hook_timestamp", "climax_timestamp"]
        for field in required_fields:
            if field not in story_analysis:
                errors.append(f"Missing required field: {field}")
                continue
            
            timestamp = story_analysis[field]
            if not isinstance(timestamp, (int, float)):
                errors.append(f"{field} must be a number")
                continue
            
            if timestamp < 0 or timestamp > self.video_duration:
                errors.append(
                    f"{field} {timestamp} is outside video range [0, {self.video_duration}]"
                )
        
        return len(errors) == 0, errors
    
    def validate_key_moments(self, key_moments: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate key moments structure"""
        errors = []
        
        if not isinstance(key_moments, list):
            return False, ["key_moments must be a list"]
        
        for i, moment in enumerate(key_moments):
            if "start" not in moment or "end" not in moment:
                errors.append(f"Key moment {i}: Missing start/end")
                continue
            
            start = float(moment["start"])
            end = float(moment["end"])
            
            if start < 0 or start > self.video_duration:
                errors.append(f"Key moment {i}: Invalid start timestamp {start}")
            
            if end < 0 or end > self.video_duration:
                errors.append(f"Key moment {i}: Invalid end timestamp {end}")
            
            if start >= end:
                errors.append(f"Key moment {i}: Start >= End")
        
        return len(errors) == 0, errors

