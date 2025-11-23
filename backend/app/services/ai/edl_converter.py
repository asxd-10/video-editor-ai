"""
EDL Converter Service
Converts LLM-generated EDL format to EditorService format
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class EDLConverter:
    """
    Converts storytelling EDL (from LLM) to EditorService EDL format.
    
    LLM Format:
    {
        "start": float,
        "end": float,
        "type": "keep" | "skip" | "transition",
        "reason": str,
        "transition_type": "fade" | "zoom" | "crossfade",
        "transition_duration": float
    }
    
    EditorService Format:
    {
        "start": float,
        "end": float,
        "type": "keep"
    }
    """
    
    def convert_llm_edl_to_editor_format(
        self,
        llm_edl: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert LLM EDL to EditorService format.
        
        Args:
            llm_edl: EDL from LLM agent (may include video_id for multi-video)
        
        Returns:
            EDL in EditorService format (preserves video_id if present)
        """
        editor_edl = []
        
        for segment in llm_edl:
            seg_type = segment.get("type", "keep")
            
            # Only include "keep" segments (skip transitions and "skip" segments)
            if seg_type == "keep":
                editor_segment = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "type": "keep"
                }
                # Preserve video_id for multi-video edits
                if "video_id" in segment:
                    editor_segment["video_id"] = segment["video_id"]
                editor_edl.append(editor_segment)
            elif seg_type == "transition":
                # Transitions are handled separately in EditorService
                # For now, we'll skip them and let EditorService handle gaps
                logger.debug(f"Skipping transition segment: {segment}")
            # Skip "skip" segments entirely
        
        # Sort by start time (for single video) or by video_id then start time (for multi-video)
        has_video_ids = any("video_id" in seg for seg in editor_edl)
        if has_video_ids:
            # For multi-video, sort by video_id first, then by start time
            editor_edl.sort(key=lambda x: (x.get("video_id", ""), x["start"]))
        else:
            editor_edl.sort(key=lambda x: x["start"])
        
        # Merge adjacent segments (only if same video_id for multi-video)
        merged = []
        for segment in editor_edl:
            if merged:
                last_seg = merged[-1]
                # Only merge if same video_id (for multi-video) or no video_id (single video)
                same_video = last_seg.get("video_id") == segment.get("video_id")
                if same_video and last_seg["end"] >= segment["start"]:
                    # Merge with previous
                    merged[-1]["end"] = max(merged[-1]["end"], segment["end"])
                else:
                    merged.append(segment)
            else:
                merged.append(segment)
        
        logger.info(f"Converted {len(llm_edl)} LLM segments to {len(merged)} editor segments")
        
        return merged
    
    def extract_transitions(
        self,
        llm_edl: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract transition information from LLM EDL.
        
        Args:
            llm_edl: EDL from LLM agent
        
        Returns:
            List of transitions [{from_timestamp, to_timestamp, type, duration}]
        """
        transitions = []
        
        for segment in llm_edl:
            if segment.get("type") == "transition":
                transitions.append({
                    "from_timestamp": segment.get("start", 0),
                    "to_timestamp": segment.get("end", 0),
                    "type": segment.get("transition_type", "fade"),
                    "duration": segment.get("transition_duration", 0.5)
                })
        
        return transitions
    
    def create_edit_options_from_plan(
        self,
        llm_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract edit options from LLM plan.
        
        Args:
            llm_plan: Full LLM response
        
        Returns:
            Edit options dict for EditorService
        """
        # Default options
        edit_options = {
            "remove_silence": False,  # LLM handles this in EDL
            "jump_cuts": True,  # LLM creates jump cuts via EDL
            "dynamic_zoom": False,  # Can enable if transitions include zoom
            "captions": True,  # Always enable captions for storytelling
            "caption_style": "burn_in",
            "pace_optimize": False,  # LLM handles pacing in EDL
            "aspect_ratios": ["16:9"]  # Default, can be overridden
        }
        
        # Check if transitions include zoom
        transitions = llm_plan.get("transitions", [])
        if any(t.get("type") == "zoom" for t in transitions):
            edit_options["dynamic_zoom"] = True
        
        return edit_options

