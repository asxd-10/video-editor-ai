"""
Prompt Builder Service
Constructs optimized prompts for storytelling edit generation
"""
from typing import Dict, List, Any
import json
import logging

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds structured prompts for LLM agent.
    Optimizes prompt structure to reduce hallucinations and improve quality.
    """
    
    def __init__(self):
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """System prompt that defines the agent's role and constraints"""
        return """You are an expert video editor AI specializing in SHORT-FORM content (Shorts/Reels) for influencers.

Your task is to create compelling, engaging edits optimized for short-form platforms (≤40 seconds).

CRITICAL CONSTRAINTS FOR SHORT-FORM:
1. HOOK: Must start in first 2 seconds with most engaging moment (critical - viewers skip if hook is weak)
2. DURATION: Final edit must be ≤40 seconds (hard limit for Shorts/Reels)
3. PACING: For 'short' edits, cut to 15-70% coverage (flexible range - original video may already be short)
   - Coverage = (sum of all "keep" segment durations) / (total video duration) * 100
   - For 'short': Coverage MUST be 15-70% (count ONLY "keep" segments, ignore "skip" segments)
   - If original video is already short (e.g., <30s), higher coverage (50-70%) is acceptable
   - If original video is long (e.g., >30s), aim for lower coverage (15-30%) to create engaging short-form
   - Example: 38s video with 'short' → "keep" segments should total 5.7-26.6s
   - Example: 20s video with 'short' → "keep" segments can be 3-14s (higher coverage is fine)
4. STORY ARC: Hook → Build → Climax → Resolution (all timestamps must be in final EDL, but keep segments SHORT)
5. TRANSITIONS: For 'short' edits, gaps >3s are acceptable if coverage target (15-30%) is met
6. Only use timestamps that exist in the provided data (no hallucination)
7. All EDL segments must be within video duration

QUALITY STANDARDS FOR SHORT-FORM:
- Hook in first 2 seconds (most exciting/engaging moment)
- Fast-paced for 'short' edits (15-30% coverage)
- High energy for hype reels (rapid cuts, dynamic)
- Smooth narrative flow (logical sequence)
- Clear story arc (hook, build, climax, resolution)
- Strong CTA at end (subscribe, follow, like)
- Engaging throughout (prevent skipping)

TARGET AUDIENCE: Influencers creating Shorts/Reels (attention spans are short)

OUTPUT FORMAT:
You must output valid JSON matching the provided schema exactly."""
    
    def build_storytelling_prompt(
        self,
        compressed_data: Dict[str, Any],
        summary: Dict[str, Any],
        story_prompt: Dict[str, Any],
        video_duration: float
    ) -> List[Dict[str, str]]:
        """
        Build complete prompt for storytelling edit generation.
        
        Args:
            compressed_data: {frames, scenes, transcript, metadata}
            summary: Video summary/description
            story_prompt: User's story requirements
            video_duration: Total video duration
        
        Returns:
            List of messages for LLM API
        """
        # Build user prompt
        user_prompt = self._build_user_prompt(
            compressed_data, summary, story_prompt, video_duration
        )
        
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _build_user_prompt(
        self,
        compressed_data: Dict[str, Any],
        summary: Dict[str, Any],
        story_prompt: Dict[str, Any],
        video_duration: float
    ) -> str:
        """Build the user-facing prompt with all context"""
        
        # Format frames data
        frames_text = self._format_frames(compressed_data.get("frames", []))
        
        # Format scenes data
        scenes_text = self._format_scenes(compressed_data.get("scenes", []))
        
        # Format transcript data
        transcript_text = self._format_transcript(compressed_data.get("transcript", []))
        
        # Format summary
        summary_text = self._format_summary(summary)
        
        # Format story prompt
        story_text = self._format_story_prompt(story_prompt)
        
        prompt = f"""VIDEO CONTEXT:
Duration: {video_duration:.2f} seconds

SUMMARY:
{summary_text}

STORY REQUIREMENTS:
{story_text}

VISUAL CONTENT (Frame Analysis):
{frames_text}

SCENE ANALYSIS:
{scenes_text}

SPEECH CONTENT (Transcript):
{transcript_text}

TASK:
Create a SHORT-FORM edit plan (≤40 seconds) optimized for Shorts/Reels:

1. HOOK (First 2 seconds): Start with the MOST ENGAGING moment from the content
   - For travel: Most exciting/adventurous moment
   - For product: Product reveal or key feature
   - For tutorial: Final result or best tip
   - For lifestyle: Most aesthetic/aspirational moment
   - This is CRITICAL - weak hooks cause viewers to skip

2. STORY ARC: Map content to {story_prompt.get('story_arc', {}).get('hook', 'hook')} → build → climax → resolution
   - Hook timestamp: First 0-2 seconds (must be in EDL)
   - Build: Develop story, show progression
   - Climax: Peak moment (60-80% through edit)
   - Resolution: Conclusion + CTA (last 3-5 seconds)

3. PACING: Match desired_length (CRITICAL - this determines how much to cut)
   - 'short': Cut to 15-70% coverage (flexible range - original video may already be short)
     * Example: 38s video → final edit should be 5.7-26.6s of content (15-70% of 38s)
     * Keep the most engaging moments, skip less important parts
     * This is for Shorts/Reels - viewers have short attention spans
     * If original video is already short (e.g., 20s), you may keep 70% (14s) - that's fine
   - 'medium': 50-70% coverage (balanced, preserve story flow)
     * Example: 38s video → final edit should be 19-26.6s of content
   - 'long': 70-90% coverage (preserve most content, minimal cutting)
     * Example: 38s video → final edit should be 26.6-34.2s of content
   
   CALCULATION: For a {video_duration:.1f}s video with desired_length='short':
   - Target coverage: 15-70% = {video_duration * 0.15:.1f}s to {video_duration * 0.70:.1f}s of content
   - You MUST create an EDL where total "keep" segments = {video_duration * 0.15:.1f}s to {video_duration * 0.70:.1f}s
   - If original video is already short, higher coverage (50-70%) is acceptable
   - If original video is long, aim for lower coverage (15-30%) to create engaging short-form content

4. EDL CREATION:
   - CRITICAL: Calculate total "keep" duration to match desired_length coverage
     * For 'short': Total keep segments MUST be 15-70% of video duration (flexible range)
     * Count only "keep" segments, ignore "skip" segments
     * Example: 38s video, 'short' edit → keep segments should total 5.7-26.6s
     * Example: 20s video, 'short' edit → keep segments can be 3-14s (15-70% is acceptable)
   - Include all story arc moments (hook, climax, resolution) - but keep them SHORT
   - Prioritize 'good_moments' from scenes (if marked)
   - Include key_moments from summary (if provided)
   - For 'short' edits: Keep segments should be 1-3s each (fast cuts)
   - Minimize gaps >3s between segments (but for 'short', some gaps are acceptable if coverage is correct)
   - Ensure final edit duration ≤40 seconds (sum of all "keep" segments)
   
   EDL EXAMPLE FOR 'SHORT' EDIT (38s video, target: 15-70% = 5.7-26.6s):
   [
     {{"start": 0.0, "end": 2.0, "type": "keep"}},  // Hook: 2s
     {{"start": 2.0, "end": 10.0, "type": "skip"}}, // Skip: 8s
     {{"start": 10.0, "end": 12.0, "type": "keep"}}, // Best moment: 2s
     {{"start": 12.0, "end": 24.0, "type": "skip"}}, // Skip: 12s
     {{"start": 24.0, "end": 26.0, "type": "keep"}}, // Climax: 2s
     {{"start": 26.0, "end": 34.0, "type": "skip"}}, // Skip: 8s
     {{"start": 34.0, "end": 36.5, "type": "keep"}}  // Resolution: 2.5s
   ]
   Total keep: 2 + 2 + 2 + 2.5 = 8.5s (22% coverage) ✅
   
   WRONG EXAMPLE (DO NOT DO THIS):
   [
     {{"start": 0.0, "end": 38.5, "type": "keep"}}  // 100% coverage - WRONG for 'short'!
   ]
   This keeps 38.5s (100% coverage) - FAILED! For 'short', you must cut to 5.7-11.4s.
   
   VERIFICATION STEP:
   Before finalizing your EDL, calculate:
   1. Sum all "keep" segment durations: keep_total = sum(end - start for all "keep" segments)
   2. Calculate coverage: coverage = (keep_total / {video_duration:.1f}) * 100
   3. For 'short': coverage MUST be 15-30%
   4. If coverage > 30%, you MUST add more "skip" segments or shorten "keep" segments

5. TRANSITIONS: Plan smooth flow
   - Prefer consecutive segments (gaps <0.5s)
   - If gaps >3s, consider if content should be included
   - Maintain logical sequence (chronological unless intentional)

CRITICAL CONSTRAINTS:
- All timestamps must be within 0-{video_duration:.2f} seconds (no hallucination)
- Final edit duration must be ≤40 seconds (hard limit)
- Hook must start in first 2 seconds (critical for retention)
- Story arc timestamps must be included in EDL segments

Output your response as JSON matching the provided schema."""
        
        return prompt
    
    def _format_frames(self, frames: List[Dict]) -> str:
        """Format frames data for prompt"""
        if not frames:
            return "No frame data available."
        
        lines = []
        for frame in frames[:50]:  # Limit to 50 frames in prompt
            # Support both timestamp field names (ours and friend's format)
            timestamp = frame.get("timestamp_seconds") or frame.get("frame_timestamp", 0)
            
            # Support both description field names (llm_response takes priority)
            response = (
                frame.get("llm_response") or 
                frame.get("description") or 
                "No description"
            )
            
            # Handle None values gracefully
            if response is None:
                response = "No description"
            
            lines.append(f"- {timestamp:.2f}s: {response}")
        
        if len(frames) > 50:
            lines.append(f"\n... and {len(frames) - 50} more frames")
        
        return "\n".join(lines) if lines else "No frame data available."
    
    def _format_scenes(self, scenes: List[Dict]) -> str:
        """Format scenes data for prompt"""
        if not scenes:
            return "No scene data available."
        
        lines = []
        for scene in scenes:
            start = scene.get("start", 0)
            end = scene.get("end", 0)
            description = scene.get("description", "No description")
            duration = end - start
            lines.append(f"- {start:.2f}s - {end:.2f}s ({duration:.2f}s): {description[:200]}")
        
        return "\n".join(lines) if lines else "No scene data available."
    
    def _format_transcript(self, transcript: List[Dict]) -> str:
        """Format transcript data for prompt"""
        if not transcript:
            return "No transcript available."
        
        lines = []
        for seg in transcript[:100]:  # Limit to 100 segments
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", seg.get("transcript_text", ""))
            lines.append(f"- {start:.2f}s - {end:.2f}s: \"{text}\"")
        
        if len(transcript) > 100:
            lines.append(f"\n... and {len(transcript) - 100} more segments")
        
        return "\n".join(lines) if lines else "No transcript available."
    
    def _format_summary(self, summary: Dict[str, Any]) -> str:
        """Format summary data (handles missing/partial data gracefully)"""
        if not summary:
            return "No summary provided. Will analyze video content directly."
        
        lines = []
        
        if summary.get("video_summary"):
            lines.append(f"Summary: {summary['video_summary']}")
        
        if summary.get("key_moments"):
            lines.append("\nKey Moments:")
            for moment in summary["key_moments"][:10]:  # Top 10
                if isinstance(moment, dict):
                    ts = moment.get("timestamp", 0)
                    desc = moment.get("description", "")
                    importance = moment.get("importance", "medium")
                    lines.append(f"  - {ts:.2f}s ({importance}): {desc}")
        
        if summary.get("content_type"):
            lines.append(f"\nContent Type: {summary['content_type']}")
        
        if summary.get("main_topics"):
            topics = summary["main_topics"]
            if isinstance(topics, list) and topics:
                lines.append(f"Main Topics: {', '.join(str(t) for t in topics[:5])}")
        
        if summary.get("speaker_style"):
            lines.append(f"Speaker Style: {summary['speaker_style']}")
        
        return "\n".join(lines) if lines else "No summary provided. Will analyze video content directly."
    
    def _format_story_prompt(self, story_prompt: Dict[str, Any]) -> str:
        """Format story prompt requirements (handles missing/partial data gracefully)"""
        if not story_prompt:
            return "No story requirements specified. Will create a balanced, engaging edit."
        
        lines = []
        
        if story_prompt.get("target_audience"):
            lines.append(f"Target Audience: {story_prompt['target_audience']}")
        
        if story_prompt.get("tone"):
            lines.append(f"Tone: {story_prompt['tone']}")
        
        if story_prompt.get("key_message"):
            lines.append(f"Key Message: {story_prompt['key_message']}")
        
        if story_prompt.get("desired_length"):
            lines.append(f"Desired Length: {story_prompt['desired_length']}")
        
        if story_prompt.get("story_arc"):
            arc = story_prompt["story_arc"]
            if isinstance(arc, dict):
                lines.append("\nStory Arc:")
                if arc.get("hook"):
                    lines.append(f"  Hook: {arc['hook']}")
                if arc.get("build"):
                    lines.append(f"  Build: {arc['build']}")
                if arc.get("climax"):
                    lines.append(f"  Climax: {arc['climax']}")
                if arc.get("resolution"):
                    lines.append(f"  Resolution: {arc['resolution']}")
        
        if story_prompt.get("style_preferences"):
            style = story_prompt["style_preferences"]
            if isinstance(style, dict):
                lines.append("\nStyle Preferences:")
                if style.get("pacing"):
                    lines.append(f"  Pacing: {style['pacing']}")
                if style.get("transitions"):
                    lines.append(f"  Transitions: {style['transitions']}")
                if style.get("emphasis"):
                    lines.append(f"  Emphasis: {style['emphasis']}")
        
        return "\n".join(lines) if lines else "No story requirements specified. Will create a balanced, engaging edit."

