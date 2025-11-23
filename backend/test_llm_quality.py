"""
Comprehensive LLM Quality Testing Framework
Tests AI edit generation with various scenarios, edge cases, and user preferences
"""
import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
from app.services.ai.data_loader import DataLoader
from app.services.ai.storytelling_agent import StorytellingAgent
from app.services.ai.edl_validator import EDLValidator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMQualityTester:
    """Framework for testing LLM response quality"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.data_loader = DataLoader(self.db)
        self.agent = StorytellingAgent()
        self.results = []
    
    def evaluate_edl_quality(self, edl: List[Dict], video_duration: float, 
                           story_prompt: Dict, summary: Dict) -> Dict[str, Any]:
        """
        Evaluate quality of generated EDL.
        Returns metrics and issues found.
        """
        issues = []
        metrics = {
            "segment_count": len(edl),
            "total_duration": sum(seg.get("end", 0) - seg.get("start", 0) for seg in edl),
            "coverage_percentage": 0.0,
            "average_segment_length": 0.0,
            "has_transitions": False,
            "valid_timestamps": True,
            "story_alignment": "unknown"
        }
        
        # Validate timestamps
        validator = EDLValidator(video_duration=video_duration)
        is_valid, errors, sanitized = validator.validate_edl(edl)
        
        if not is_valid:
            issues.extend([f"Validation error: {e}" for e in errors])
            metrics["valid_timestamps"] = False
        
        # Calculate coverage
        if video_duration > 0:
            metrics["coverage_percentage"] = (metrics["total_duration"] / video_duration) * 100
        
        # Calculate average segment length
        if len(edl) > 0:
            metrics["average_segment_length"] = metrics["total_duration"] / len(edl)
        
        # Check for transitions
        metrics["has_transitions"] = any(seg.get("type") == "transition" for seg in edl)
        
        # Check story alignment (basic heuristics)
        desired_length = story_prompt.get("desired_length", "medium")
        if desired_length == "short" and metrics["total_duration"] > video_duration * 0.3:
            issues.append("Desired 'short' edit but duration is >30% of original")
        elif desired_length == "long" and metrics["total_duration"] < video_duration * 0.5:
            issues.append("Desired 'long' edit but duration is <50% of original")
        
        # Check for empty EDL
        if len(edl) == 0:
            issues.append("CRITICAL: EDL is empty")
        
        # Check for very short segments
        short_segments = [seg for seg in edl if (seg.get("end", 0) - seg.get("start", 0)) < 1.0]
        if len(short_segments) > len(edl) * 0.3:
            issues.append(f"Too many very short segments ({len(short_segments)}/{len(edl)})")
        
        # Check for gaps (potential jump cuts)
        sorted_edl = sorted(edl, key=lambda x: x.get("start", 0))
        large_gaps = []
        for i in range(len(sorted_edl) - 1):
            gap = sorted_edl[i+1]["start"] - sorted_edl[i]["end"]
            if gap > 5.0:  # Gap > 5 seconds
                large_gaps.append(gap)
        
        if len(large_gaps) > 0:
            metrics["large_gaps"] = len(large_gaps)
            issues.append(f"Found {len(large_gaps)} large gaps (>5s) - may indicate missing content")
        
        return {
            "metrics": metrics,
            "issues": issues,
            "score": self._calculate_score(metrics, issues)
        }
    
    def _calculate_score(self, metrics: Dict, issues: List[str]) -> float:
        """Calculate quality score (0-100)"""
        score = 100.0
        
        # Deduct for issues
        score -= len(issues) * 5  # -5 per issue
        
        # Deduct for validation errors
        if not metrics.get("valid_timestamps"):
            score -= 20
        
        # Deduct for empty EDL
        if metrics.get("segment_count", 0) == 0:
            score = 0
        
        # Bonus for good coverage (if desired)
        if 20 <= metrics.get("coverage_percentage", 0) <= 80:
            score += 10
        
        # Bonus for reasonable segment count
        if 3 <= metrics.get("segment_count", 0) <= 20:
            score += 10
        
        return max(0, min(100, score))
    
    async def test_scenario(
        self,
        video_id: str,
        scenario_name: str,
        story_prompt: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
        expected_behavior: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test a single scenario.
        
        Args:
            video_id: Video to test
            scenario_name: Name of test scenario
            story_prompt: User preferences
            summary: Video description (optional - will load from DB if None)
            expected_behavior: What we expect (for documentation)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Scenario: {scenario_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Load video data
            data = self.data_loader.load_all_data(video_id)
            video_duration = data.get("video_duration", 0.0)
            
            if video_duration == 0:
                return {
                    "scenario": scenario_name,
                    "status": "skipped",
                    "reason": "Video duration is 0"
                }
            
            # Use provided summary or load from data
            if summary is None:
                summary = data.get("summary", {})
            
            # Extract transcript segments
            transcript_segments = self.data_loader.extract_transcript_segments(
                data.get("transcription")
            )
            
            logger.info(f"Video duration: {video_duration:.2f}s")
            logger.info(f"Frames: {len(data.get('frames', []))}")
            logger.info(f"Scenes: {len(data.get('scenes', []))}")
            logger.info(f"Transcript segments: {len(transcript_segments)}")
            logger.info(f"Story prompt: {json.dumps(story_prompt, indent=2)}")
            logger.info(f"Summary: {json.dumps(summary, indent=2)}")
            
            # Generate edit plan
            logger.info("Generating edit plan...")
            start_time = datetime.now()
            
            plan = await self.agent.generate_edit_plan(
                frames=data.get("frames", []),
                scenes=data.get("scenes", []),
                transcript_segments=transcript_segments,
                summary=summary,
                story_prompt=story_prompt,
                video_duration=video_duration
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Extract EDL
            edl = plan.get("edl", [])
            story_analysis = plan.get("story_analysis", {})
            key_moments = plan.get("key_moments", [])
            
            logger.info(f"Generation completed in {elapsed:.2f}s")
            logger.info(f"EDL segments: {len(edl)}")
            logger.info(f"Key moments: {len(key_moments)}")
            
            # Evaluate quality
            evaluation = self.evaluate_edl_quality(edl, video_duration, story_prompt, summary)
            
            # Log results
            logger.info(f"\nQuality Score: {evaluation['score']:.1f}/100")
            logger.info(f"Metrics: {json.dumps(evaluation['metrics'], indent=2)}")
            
            if evaluation['issues']:
                logger.warning(f"Issues found ({len(evaluation['issues'])}):")
                for issue in evaluation['issues']:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✅ No issues found")
            
            # Store result
            result = {
                "scenario": scenario_name,
                "video_id": video_id,
                "status": "success",
                "elapsed_seconds": elapsed,
                "story_prompt": story_prompt,
                "summary": summary,
                "edl": edl,
                "story_analysis": story_analysis,
                "key_moments": key_moments,
                "evaluation": evaluation,
                "expected_behavior": expected_behavior,
                "timestamp": datetime.now().isoformat()
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Scenario failed: {e}", exc_info=True)
            result = {
                "scenario": scenario_name,
                "video_id": video_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.results.append(result)
            return result
    
    def generate_report(self, output_file: str = "llm_quality_report.json"):
        """Generate comprehensive test report"""
        report = {
            "test_run": datetime.now().isoformat(),
            "total_scenarios": len(self.results),
            "successful": sum(1 for r in self.results if r.get("status") == "success"),
            "failed": sum(1 for r in self.results if r.get("status") == "failed"),
            "skipped": sum(1 for r in self.results if r.get("status") == "skipped"),
            "average_score": sum(
                r.get("evaluation", {}).get("score", 0) 
                for r in self.results 
                if r.get("status") == "success"
            ) / max(1, sum(1 for r in self.results if r.get("status") == "success")),
            "results": self.results
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("TEST REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Total scenarios: {report['total_scenarios']}")
        logger.info(f"Successful: {report['successful']}")
        logger.info(f"Failed: {report['failed']}")
        logger.info(f"Skipped: {report['skipped']}")
        logger.info(f"Average score: {report['average_score']:.1f}/100")
        logger.info(f"\nReport saved to: {output_file}")
        
        return report


# Test Scenarios
SCENARIOS = {
    "educational_short": {
        "name": "Educational Video - Short Edit",
        "story_prompt": {
            "target_audience": "students",
            "tone": "educational",
            "key_message": "Focus on main concepts and examples",
            "desired_length": "short",
            "story_arc": {
                "hook": "Start with a question or problem",
                "build": "Explain concepts clearly",
                "climax": "Show practical example",
                "resolution": "Summarize key takeaways"
            },
            "style_preferences": {
                "pacing": "fast",
                "transitions": "smooth",
                "emphasis": "on_examples"
            }
        },
        "summary": {
            "video_summary": "Educational tutorial explaining a technical concept with examples",
            "content_type": "tutorial",
            "main_topics": ["concept explanation", "examples", "practical applications"],
            "speaker_style": "professional"
        },
        "expected": "Should create a concise edit focusing on key concepts and examples, removing filler"
    },
    
    "vlog_casual": {
        "name": "Vlog - Casual, Engaging",
        "story_prompt": {
            "target_audience": "general",
            "tone": "casual",
            "key_message": "Show personality and authentic moments",
            "desired_length": "medium",
            "story_arc": {
                "hook": "Grab attention in first 3 seconds",
                "build": "Build connection with audience",
                "climax": "Main story or revelation",
                "resolution": "Call to action or reflection"
            },
            "style_preferences": {
                "pacing": "moderate",
                "transitions": "smooth",
                "emphasis": "on_personality"
            }
        },
        "summary": {
            "video_summary": "Casual vlog sharing daily experiences and thoughts",
            "content_type": "vlog",
            "main_topics": ["daily life", "personal thoughts", "experiences"],
            "speaker_style": "casual"
        },
        "expected": "Should preserve authentic moments, remove dead air, maintain casual feel"
    },
    
    "tutorial_detailed": {
        "name": "Tutorial - Detailed Step-by-Step",
        "story_prompt": {
            "target_audience": "beginners",
            "tone": "instructional",
            "key_message": "Clear step-by-step instructions",
            "desired_length": "long",
            "story_arc": {
                "hook": "Show end result or preview",
                "build": "Step-by-step instructions",
                "climax": "Key technique or tip",
                "resolution": "Final result and next steps"
            },
            "style_preferences": {
                "pacing": "slow",
                "transitions": "smooth",
                "emphasis": "on_steps"
            }
        },
        "summary": {
            "video_summary": "Detailed tutorial with step-by-step instructions",
            "content_type": "tutorial",
            "main_topics": ["step 1", "step 2", "step 3", "tips"],
            "speaker_style": "instructional"
        },
        "expected": "Should preserve all important steps, maintain logical flow, keep detailed explanations"
    },
    
    "minimal_prompt": {
        "name": "Edge Case - Minimal Story Prompt",
        "story_prompt": {
            "tone": "educational"
        },
        "summary": {
            "video_summary": "Test video"
        },
        "expected": "Should handle gracefully with minimal input, use defaults"
    },
    
    "empty_summary": {
        "name": "Edge Case - Empty Summary",
        "story_prompt": {
            "target_audience": "general",
            "tone": "educational",
            "desired_length": "medium"
        },
        "summary": {},
        "expected": "Should analyze frames and transcript directly, not rely on summary"
    },
    
    "contradictory_preferences": {
        "name": "Edge Case - Contradictory Preferences",
        "story_prompt": {
            "target_audience": "students",
            "tone": "educational",
            "desired_length": "short",  # Short
            "style_preferences": {
                "pacing": "slow"  # But slow pacing (contradictory)
            }
        },
        "summary": {
            "video_summary": "Educational content"
        },
        "expected": "Should prioritize desired_length over pacing, or find balance"
    },
    
    "very_long_video": {
        "name": "Edge Case - Very Long Video (30+ min)",
        "story_prompt": {
            "target_audience": "general",
            "tone": "educational",
            "desired_length": "short",
            "key_message": "Extract only the most important moments"
        },
        "summary": {
            "video_summary": "Long-form educational content"
        },
        "expected": "Should aggressively cut to create short edit from long video"
    },
    
    "very_short_video": {
        "name": "Edge Case - Very Short Video (<2 min)",
        "story_prompt": {
            "target_audience": "general",
            "tone": "casual",
            "desired_length": "medium"
        },
        "summary": {
            "video_summary": "Short video content"
        },
        "expected": "Should preserve most content, minimal cutting"
    }
}


async def run_all_tests(video_id: str, scenarios_to_run: Optional[List[str]] = None):
    """Run all test scenarios"""
    tester = LLMQualityTester()
    
    scenarios = scenarios_to_run if scenarios_to_run else list(SCENARIOS.keys())
    
    for scenario_key in scenarios:
        scenario = SCENARIOS[scenario_key]
        await tester.test_scenario(
            video_id=video_id,
            scenario_name=scenario["name"],
            story_prompt=scenario["story_prompt"],
            summary=scenario.get("summary"),
            expected_behavior=scenario.get("expected")
        )
    
    # Generate report
    report = tester.generate_report()
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_llm_quality.py <video_id> [scenario1,scenario2,...]")
        print("\nAvailable scenarios:")
        for key, scenario in SCENARIOS.items():
            print(f"  - {key}: {scenario['name']}")
        print("\nExample:")
        print("  python test_llm_quality.py f5b0c7ad-ab9c-4e21-bfbd-a4a197c36d95")
        print("  python test_llm_quality.py f5b0c7ad-ab9c-4e21-bfbd-a4a197c36d95 educational_short,vlog_casual")
        sys.exit(1)
    
    video_id = sys.argv[1]
    scenarios = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    
    asyncio.run(run_all_tests(video_id, scenarios))

