"""
Comprehensive Short-Form Content LLM Quality Testing
Focus: Influencers/Shorts/Reels, 40s max, prompt optimization
"""
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.media import Media
from app.models.aidit_models import Frame, SceneIndex, Transcription
from app.services.ai.data_loader import DataLoader
from app.services.ai.storytelling_agent import StorytellingAgent
from app.services.ai.edl_validator import EDLValidator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShortFormQualityEvaluator:
    """Evaluator specifically for short-form content (Shorts/Reels)"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.data_loader = DataLoader(self.db)
        self.agent = StorytellingAgent()
        self.results = []
    
    def evaluate_short_form_quality(
        self,
        edl: List[Dict],
        story_analysis: Dict,
        key_moments: List[Dict],
        video_duration: float,
        story_prompt: Dict,
        expected_coverage: str,
        expected_segments: str
    ) -> Dict[str, Any]:
        """
        Evaluate quality specifically for short-form content.
        
        Criteria:
        1. Hook effectiveness (first 2-3 seconds)
        2. Pacing matches desired_length
        3. Story arc is followed
        4. Transitions make sense
        5. Coverage is appropriate
        6. Segments flow logically
        7. Meets influencer/shorts/reels standards
        """
        issues = []
        strengths = []
        # Calculate coverage: only count "keep" segments, ignore "skip" segments
        keep_segments = [seg for seg in edl if seg.get("type") == "keep"]
        keep_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in keep_segments)
        
        metrics = {
            "total_duration": keep_duration,  # Only "keep" segments count
            "segment_count": len(edl),
            "coverage_percentage": (keep_duration / video_duration * 100) if video_duration > 0 else 0,
            "hook_effectiveness": "unknown",
            "pacing_score": 0,
            "story_arc_score": 0,
            "transition_quality": "unknown",
            "flow_score": 0
        }
        
        # 1. Hook Evaluation (first 2-3 seconds)
        if edl:
            first_segment = edl[0]
            hook_start = first_segment.get("start", 0)
            hook_end = first_segment.get("end", 0)
            
            if hook_start <= 2.0:  # Hook should start very early
                if hook_end - hook_start >= 1.5:  # Hook should be substantial
                    metrics["hook_effectiveness"] = "good"
                    strengths.append("Strong hook in first 2 seconds")
                else:
                    metrics["hook_effectiveness"] = "weak"
                    issues.append("Hook segment too short (<1.5s)")
            else:
                metrics["hook_effectiveness"] = "late"
                issues.append("Hook starts too late (>2s) - critical for shorts/reels")
        
        # 2. Pacing Evaluation
        desired_length = story_prompt.get("desired_length", "medium")
        coverage = metrics["coverage_percentage"]
        
        if desired_length == "short":
            if 15 <= coverage <= 70:
                metrics["pacing_score"] = 100
                strengths.append("Perfect pacing for short edit")
            elif coverage < 15:
                metrics["pacing_score"] = 70
                issues.append("Coverage too low for short edit (<15%)")
            elif coverage > 70:
                metrics["pacing_score"] = 50
                issues.append("Coverage too high for short edit (>70%)")
        elif desired_length == "medium":
            if 50 <= coverage <= 70:
                metrics["pacing_score"] = 100
                strengths.append("Perfect pacing for medium edit")
            elif coverage < 50:
                metrics["pacing_score"] = 70
                issues.append("Coverage too low for medium edit (<50%)")
            elif coverage > 70:
                metrics["pacing_score"] = 50
                issues.append("Coverage too high for medium edit (>70%)")
        else:  # long
            if 70 <= coverage <= 90:
                metrics["pacing_score"] = 100
                strengths.append("Perfect pacing for long edit")
            else:
                metrics["pacing_score"] = 70
        
        # 3. Story Arc Evaluation
        if story_analysis:
            hook_ts = story_analysis.get("hook_timestamp", -1)
            climax_ts = story_analysis.get("climax_timestamp", -1)
            resolution_ts = story_analysis.get("resolution_timestamp", -1)
            
            # Check if timestamps are in EDL
            hook_in_edl = any(
                seg.get("start", 0) <= hook_ts <= seg.get("end", 0) 
                for seg in edl
            ) if hook_ts >= 0 else False
            
            climax_in_edl = any(
                seg.get("start", 0) <= climax_ts <= seg.get("end", 0) 
                for seg in edl
            ) if climax_ts >= 0 else False
            
            if hook_in_edl and climax_in_edl:
                metrics["story_arc_score"] = 100
                strengths.append("Story arc moments included in edit")
            elif hook_in_edl or climax_in_edl:
                metrics["story_arc_score"] = 70
                issues.append("Some story arc moments missing from edit")
            else:
                metrics["story_arc_score"] = 30
                issues.append("Story arc moments not included in edit")
        
        # 4. Transition Quality
        sorted_edl = sorted(edl, key=lambda x: x.get("start", 0))
        large_gaps = []
        smooth_transitions = 0
        
        for i in range(len(sorted_edl) - 1):
            gap = sorted_edl[i+1]["start"] - sorted_edl[i]["end"]
            if gap > 3.0:  # Large gap
                large_gaps.append(gap)
            elif gap < 0.5:  # Smooth transition
                smooth_transitions += 1
        
        if len(large_gaps) == 0:
            metrics["transition_quality"] = "smooth"
            strengths.append("Smooth transitions throughout")
        elif len(large_gaps) <= 2:
            metrics["transition_quality"] = "mostly_smooth"
            issues.append(f"{len(large_gaps)} large gaps (>3s) - may need transitions")
        else:
            metrics["transition_quality"] = "choppy"
            issues.append(f"{len(large_gaps)} large gaps - edit feels choppy")
        
        # 5. Flow Evaluation (logical sequence)
        # Check if segments are in chronological order
        is_chronological = all(
            sorted_edl[i]["start"] <= sorted_edl[i+1]["start"]
            for i in range(len(sorted_edl) - 1)
        )
        
        # Check for very short segments that might feel rushed
        very_short_segments = [
            seg for seg in edl 
            if (seg.get("end", 0) - seg.get("start", 0)) < 1.0
        ]
        
        if is_chronological and len(very_short_segments) <= 2:
            metrics["flow_score"] = 100
            strengths.append("Good flow, logical sequence")
        elif is_chronological:
            metrics["flow_score"] = 80
            issues.append(f"{len(very_short_segments)} very short segments (<1s) - may feel rushed")
        else:
            metrics["flow_score"] = 60
            issues.append("Segments not in chronological order - may confuse viewers")
        
        # 6. Short-Form Specific Checks
        short_form_issues = []
        
        # Check if edit is too long for shorts/reels (only count "keep" segments)
        if metrics["total_duration"] > 40:
            short_form_issues.append(f"Edit too long ({metrics['total_duration']:.1f}s) for shorts/reels (max 40s)")
        
        # Check if hook is strong enough
        if metrics["hook_effectiveness"] in ["weak", "late"]:
            short_form_issues.append("Hook not strong enough for short-form content")
        
        # Check if pacing is too slow (only flag if >70% for short edits)
        if desired_length == "short" and metrics["coverage_percentage"] > 70:
            short_form_issues.append("Pacing too slow for short-form - coverage >70%")
        
        issues.extend(short_form_issues)
        
        # Calculate overall score
        score = self._calculate_short_form_score(metrics, issues, strengths)
        
        return {
            "metrics": metrics,
            "issues": issues,
            "strengths": strengths,
            "score": score,
            "short_form_ready": score >= 75 and len(short_form_issues) == 0
        }
    
    def _calculate_short_form_score(self, metrics: Dict, issues: List[str], strengths: List[str]) -> float:
        """Calculate quality score for short-form content (0-100)"""
        score = 100.0
        
        # Deduct for issues
        score -= len(issues) * 5
        
        # Hook is critical for shorts/reels
        if metrics.get("hook_effectiveness") == "good":
            score += 10
        elif metrics.get("hook_effectiveness") in ["weak", "late"]:
            score -= 20
        
        # Pacing is critical
        score += (metrics.get("pacing_score", 0) - 50) * 0.2
        
        # Story arc
        score += (metrics.get("story_arc_score", 0) - 50) * 0.15
        
        # Transitions
        if metrics.get("transition_quality") == "smooth":
            score += 10
        elif metrics.get("transition_quality") == "choppy":
            score -= 15
        
        # Flow
        score += (metrics.get("flow_score", 0) - 50) * 0.1
        
        # Bonus for strengths
        score += len(strengths) * 3
        
        return max(0, min(100, score))
    
    async def test_video_scenario(
        self,
        video_data: Dict,
        scenario: Dict
    ) -> Dict[str, Any]:
        """Test a single video with a scenario"""
        video_id = video_data["video_id"]
        scenario_name = scenario["name"]
        story_prompt = scenario["story_prompt"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {video_id} - {scenario_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Simulate data (in real test, this would come from database)
            frames = [
                {
                    "timestamp_seconds": f.get("frame_timestamp", 0),
                    "llm_response": f.get("description", ""),
                    "status": "completed"
                }
                for f in video_data.get("frame_level_data", [])
            ]
            
            scenes = video_data.get("scene_level_data", {}).get("scenes", [])
            transcript_segments = video_data.get("transcript_data", [])
            
            summary = {
                "video_summary": video_data.get("description", ""),
                "key_moments": [
                    {
                        "timestamp": scene.get("start", 0),
                        "description": scene.get("description", ""),
                        "importance": scene.get("metadata", {}).get("importance", "medium")
                    }
                    for scene in scenes
                    if scene.get("metadata", {}).get("good_moment", False)
                ]
            }
            
            video_duration = video_data.get("duration", 0)
            
            logger.info(f"Video duration: {video_duration:.1f}s")
            logger.info(f"Frames: {len(frames)}")
            logger.info(f"Scenes: {len(scenes)}")
            logger.info(f"Transcript segments: {len(transcript_segments)}")
            logger.info(f"Story prompt: {json.dumps(story_prompt, indent=2)}")
            
            # Generate edit plan
            logger.info("Generating edit plan...")
            start_time = datetime.now()
            
            plan = await self.agent.generate_edit_plan(
                frames=frames,
                scenes=scenes,
                transcript_segments=transcript_segments,
                summary=summary,
                story_prompt=story_prompt,
                video_duration=video_duration
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            edl = plan.get("edl", [])
            story_analysis = plan.get("story_analysis", {})
            key_moments = plan.get("key_moments", [])
            
            logger.info(f"Generation completed in {elapsed:.2f}s")
            logger.info(f"EDL segments: {len(edl)}")
            
            # Evaluate quality
            evaluation = self.evaluate_short_form_quality(
                edl=edl,
                story_analysis=story_analysis,
                key_moments=key_moments,
                video_duration=video_duration,
                story_prompt=story_prompt,
                expected_coverage=scenario.get("expected_edl_coverage", ""),
                expected_segments=scenario.get("expected_segments", "")
            )
            
            # Log results
            logger.info(f"\nQuality Score: {evaluation['score']:.1f}/100")
            logger.info(f"Short-form Ready: {'✅' if evaluation['short_form_ready'] else '❌'}")
            logger.info(f"Coverage: {evaluation['metrics']['coverage_percentage']:.1f}%")
            logger.info(f"Segments: {evaluation['metrics']['segment_count']}")
            logger.info(f"Hook: {evaluation['metrics']['hook_effectiveness']}")
            logger.info(f"Pacing: {evaluation['metrics']['pacing_score']}/100")
            logger.info(f"Story Arc: {evaluation['metrics']['story_arc_score']}/100")
            logger.info(f"Transitions: {evaluation['metrics']['transition_quality']}")
            logger.info(f"Flow: {evaluation['metrics']['flow_score']}/100")
            
            if evaluation['strengths']:
                logger.info(f"\n✅ Strengths:")
                for strength in evaluation['strengths']:
                    logger.info(f"  - {strength}")
            
            if evaluation['issues']:
                logger.warning(f"\n⚠️  Issues ({len(evaluation['issues'])}):")
                for issue in evaluation['issues']:
                    logger.warning(f"  - {issue}")
            
            # Show EDL
            logger.info(f"\n📋 Generated EDL:")
            for i, seg in enumerate(edl[:10], 1):  # Show first 10
                logger.info(f"  {i}. {seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s ({seg.get('type', 'keep')})")
            if len(edl) > 10:
                logger.info(f"  ... and {len(edl) - 10} more segments")
            
            result = {
                "video_id": video_id,
                "scenario": scenario_name,
                "status": "success",
                "elapsed_seconds": elapsed,
                "story_prompt": story_prompt,
                "edl": edl,
                "story_analysis": story_analysis,
                "key_moments": key_moments,
                "evaluation": evaluation,
                "expected": scenario.get("expected_quality", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            result = {
                "video_id": video_id,
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.results.append(result)
            return result
    
    def generate_report(self, output_file: str = "short_form_quality_report.json"):
        """Generate comprehensive test report"""
        report = {
            "test_run": datetime.now().isoformat(),
            "target_audience": "Influencers/Shorts/Reels",
            "max_video_length": "40 seconds",
            "total_tests": len(self.results),
            "successful": sum(1 for r in self.results if r.get("status") == "success"),
            "failed": sum(1 for r in self.results if r.get("status") == "failed"),
            "short_form_ready": sum(
                1 for r in self.results 
                if r.get("evaluation", {}).get("short_form_ready", False)
            ),
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
        logger.info("SHORT-FORM QUALITY TEST REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Total tests: {report['total_tests']}")
        logger.info(f"Successful: {report['successful']}")
        logger.info(f"Failed: {report['failed']}")
        logger.info(f"Short-form Ready: {report['short_form_ready']}/{report['successful']}")
        logger.info(f"Average Score: {report['average_score']:.1f}/100")
        logger.info(f"\nReport saved to: {output_file}")
        
        return report


async def run_short_form_tests(test_data_file: str = "test_dataset_short_form.json"):
    """Run all short-form quality tests"""
    # Load test dataset
    with open(test_data_file, 'r') as f:
        test_data = json.load(f)
    
    evaluator = ShortFormQualityEvaluator()
    
    # Test all videos and scenarios
    for video_data in test_data.get("test_videos", []):
        for scenario in video_data.get("test_scenarios", []):
            await evaluator.test_video_scenario(video_data, scenario)
    
    # Test edge cases
    for video_data in test_data.get("edge_case_videos", []):
        for scenario in video_data.get("test_scenarios", []):
            await evaluator.test_video_scenario(video_data, scenario)
    
    # Generate report
    report = evaluator.generate_report()
    return report


if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "test_dataset_short_form.json"
    asyncio.run(run_short_form_tests(test_file))

