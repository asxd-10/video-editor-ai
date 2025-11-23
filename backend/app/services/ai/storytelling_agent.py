"""
Storytelling Agent Service
Main orchestrator for AI-driven storytelling edits
"""
from typing import Dict, List, Any, Optional
import logging
import json

from app.services.ai.llm_client import LLMClient
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.data_compressor import DataCompressor
from app.services.ai.edl_validator import EDLValidator

logger = logging.getLogger(__name__)


class StorytellingAgent:
    """
    AI Agent that creates storytelling edits using LLM.
    
    Workflow:
    1. Load and compress data (frames, scenes, transcript)
    2. Build optimized prompt
    3. Call LLM with structured output schema
    4. Validate response (prevent hallucinations)
    5. Return validated edit plan
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        data_compressor: Optional[DataCompressor] = None
    ):
        """
        Args:
            llm_client: LLM client instance (creates new if None)
            data_compressor: Data compressor instance (creates new if None)
        """
        self.llm_client = llm_client or LLMClient()
        self.data_compressor = data_compressor or DataCompressor()
        self.prompt_builder = PromptBuilder()
    
    async def generate_edit_plan(
        self,
        frames: List[Dict],
        scenes: List[Dict],
        transcript_segments: List[Dict],
        summary: Dict[str, Any],
        story_prompt: Dict[str, Any],
        video_duration: float,
        video_ids: Optional[List[str]] = None,
        videos_metadata: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate storytelling edit plan using LLM agent.
        
        Args:
            frames: Frame data with LLM responses (may include source_video_id)
            scenes: Scene data with descriptions (may include source_video_id)
            transcript_segments: Transcript segments
            summary: Video summary/description
            story_prompt: User's story requirements
            video_duration: Total video duration
            video_ids: Optional list of video IDs (for multi-video edits)
            videos_metadata: Optional list of video metadata dicts
        
        Returns:
            {
                "edl": [...],  # Validated Edit Decision List (with video_id for each segment)
                "story_analysis": {...},
                "key_moments": [...],
                "transitions": [...],
                "recommendations": [...],
                "metadata": {
                    "compression_ratios": {...},
                    "validation_errors": [...],
                    "llm_usage": {...}
                }
            }
        """
        is_multi_video = video_ids and len(video_ids) > 1
        if is_multi_video:
            logger.info(f"Generating storytelling edit plan for {len(video_ids)} videos ({video_duration:.2f}s total)")
        else:
            logger.info(f"Generating storytelling edit plan for {video_duration:.2f}s video")
        
        # Step 1: Compress data
        logger.info("Compressing data for LLM context...")
        compressed_data = self.data_compressor.create_context_summary(
            frames=frames,
            scenes=scenes,
            transcript_segments=transcript_segments,
            video_duration=video_duration
        )
        
        logger.info(
            f"Data compressed: {compressed_data['metadata']['compressed_frames']} frames, "
            f"{compressed_data['metadata']['compressed_scenes']} scenes, "
            f"{compressed_data['metadata']['compressed_segments']} transcript segments"
        )
        
        # Step 2: Build prompt
        logger.info("Building LLM prompt...")
        messages = self.prompt_builder.build_storytelling_prompt(
            compressed_data=compressed_data,
            summary=summary,
            story_prompt=story_prompt,
            video_duration=video_duration,
            video_ids=video_ids,
            videos_metadata=videos_metadata
        )
        
        # Step 3: Define JSON schema for structured output
        json_schema = self._get_edl_schema(video_duration, video_ids=video_ids)
        
        # Step 4: Call LLM
        logger.info("Calling LLM agent...")
        try:
            llm_response = await self.llm_client.generate_structured(
                messages=messages,
                json_schema=json_schema,
                temperature=0.3  # Lower temperature for consistency
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
        
        # Step 5: Validate response
        logger.info("Validating LLM response...")
        validator = EDLValidator(video_duration=video_duration)
        
        # Validate EDL
        edl_valid, edl_errors, sanitized_edl = validator.validate_edl(
            llm_response.get("edl", [])
        )
        
        # Validate story analysis
        story_valid, story_errors = validator.validate_story_analysis(
            llm_response.get("story_analysis", {})
        )
        
        # Validate key moments
        moments_valid, moments_errors = validator.validate_key_moments(
            llm_response.get("key_moments", [])
        )
        
        all_errors = edl_errors + story_errors + moments_errors
        
        if not edl_valid:
            logger.warning(f"EDL validation found issues: {all_errors}")
            # Continue with sanitized EDL if possible
        
        # Step 6: Return validated plan
        result = {
            "edl": sanitized_edl if sanitized_edl else llm_response.get("edl", []),
            "story_analysis": llm_response.get("story_analysis", {}),
            "key_moments": llm_response.get("key_moments", []),
            "transitions": llm_response.get("transitions", []),
            "recommendations": llm_response.get("recommendations", []),
            "metadata": {
                "compression_ratios": compressed_data["metadata"],
                "validation_errors": all_errors,
                "validation_passed": edl_valid and story_valid and moments_valid,
                "llm_usage": llm_response.get("usage", {})
            }
        }
        
        logger.info(f"Edit plan generated: {len(sanitized_edl)} segments, {len(all_errors)} validation issues")
        
        return result
    
    def _get_edl_schema(self, video_duration: float, video_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get JSON schema for structured LLM output"""
        is_multi_video = video_ids and len(video_ids) > 1
        
        # EDL segment properties
        edl_segment_properties = {
            "start": {
                "type": "number",
                "minimum": 0,
                "maximum": video_duration
            },
            "end": {
                "type": "number",
                "minimum": 0,
                "maximum": video_duration
            },
            "type": {
                "type": "string",
                "enum": ["keep", "skip", "transition"]
            },
            "reason": {"type": "string"},
            "transition_type": {
                "type": "string",
                "enum": ["fade", "zoom", "crossfade"]
            },
            "transition_duration": {
                "type": "number",
                "minimum": 0,
                "maximum": 2.0
            }
        }
        
        # Add video_id field for multi-video edits
        if is_multi_video:
            edl_segment_properties["video_id"] = {
                "type": "string",
                "enum": video_ids,
                "description": "ID of the source video for this segment"
            }
        
        return {
            "type": "object",
            "properties": {
                "story_analysis": {
                    "type": "object",
                    "properties": {
                        "hook_timestamp": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": video_duration,
                            "description": "Timestamp of hook moment (attention-grabbing start)"
                        },
                        "climax_timestamp": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": video_duration,
                            "description": "Timestamp of climax moment (main point/revelation)"
                        },
                        "resolution_timestamp": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": video_duration,
                            "description": "Timestamp of resolution (conclusion)"
                        }
                    },
                    "required": ["hook_timestamp", "climax_timestamp"]
                },
                "key_moments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": video_duration
                            },
                            "end": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": video_duration
                            },
                            "importance": {
                                "type": "string",
                                "enum": ["high", "medium", "low"]
                            },
                            "reason": {"type": "string"},
                            "story_role": {
                                "type": "string",
                                "enum": ["hook", "build", "climax", "resolution", "transition"]
                            }
                        },
                        "required": ["start", "end", "importance", "reason"]
                    }
                },
                "transitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from_timestamp": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": video_duration
                            },
                            "to_timestamp": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": video_duration
                            },
                            "type": {
                                "type": "string",
                                "enum": ["cut", "fade", "zoom", "crossfade"]
                            },
                            "duration": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 2.0
                            },
                            "reason": {"type": "string"}
                        },
                        "required": ["from_timestamp", "to_timestamp", "type"]
                    }
                },
                "edl": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": edl_segment_properties,
                        "required": ["start", "end", "type"] + (["video_id"] if is_multi_video else [])
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "timestamp": {"type": "number"},
                            "message": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"]
                            }
                        },
                        "required": ["type", "message"]
                    }
                }
            },
            "required": ["edl", "story_analysis", "key_moments"]
        }
    
    async def close(self):
        """Cleanup resources"""
        if self.llm_client:
            await self.llm_client.close()

