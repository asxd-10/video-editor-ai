# Short-Form Content Testing - Quick Start

## Goal
Test and optimize LLM prompts to create **awesome short-form edits** (Shorts/Reels) that are:
- Engaging (hook in first 2s)
- Fast-paced (15-30% coverage for short edits)
- Story-driven (clear arc)
- Smooth (good transitions)
- ≤40 seconds

## Quick Start (3 Steps)

### Step 1: Insert Test Data
```bash
python insert_test_data.py test_dataset_short_form.json
```

This creates 5 realistic test videos with:
- Frame descriptions (friend's format)
- Scene data
- Transcripts
- Multiple test scenarios per video

### Step 2: Run Quality Tests
```bash
python test_short_form_quality.py test_dataset_short_form.json
```

This tests:
- Hook effectiveness (first 2s)
- Pacing (coverage %)
- Story arc (hook/climax/resolution)
- Transitions (gaps)
- Flow (logical sequence)
- Short-form readiness (≤40s, engaging)

### Step 3: Review & Optimize
```bash
cat short_form_quality_report.json | jq .
```

Look for:
- Average score (target: >80/100)
- Short-form ready count
- Common issues (hook, pacing, transitions)
- Patterns across scenarios

## Test Dataset

### Videos:
1. **Travel vlog** (38.5s) - 3 scenarios
2. **Product review** (35.0s) - 1 scenario
3. **Day in life** (28.0s) - 1 scenario
4. **Cooking tutorial** (25.0s) - 1 scenario
5. **Fitness workout** (32.0s) - 1 scenario
6. **Edge cases** - Very short (15s), Max length (40s)

### Scenarios:
- High energy hype reel
- Nostalgic summer vibes
- Quick tips tutorial
- Aesthetic lifestyle
- Motivational workout

## Evaluation Criteria

### Hook (Critical)
- ✅ Good: Starts in first 2s, ≥1.5s duration
- ⚠️ Weak: Too short or starts late
- Score impact: -20 if weak/late

### Pacing
- Short: 15-30% coverage (target)
- Medium: 50-70% coverage
- Long: 70-90% coverage

### Story Arc
- Hook, Build, Climax, Resolution must be in EDL
- Timestamps must align with segments
- Score: 100 if all present, 30 if none

### Transitions
- Smooth: No gaps >3s
- Mostly smooth: 1-2 gaps >3s
- Choppy: Many gaps >3s

### Short-Form Ready
- Total duration ≤40s
- Hook is strong
- Pacing appropriate
- Story arc clear
- Transitions smooth

## Prompt Optimization

### Current Enhancements:
1. ✅ Emphasized hook requirement (first 2s)
2. ✅ Added 40s duration limit
3. ✅ Added pacing guidelines (15-30% for short)
4. ✅ Strengthened story arc requirements
5. ✅ Added transition guidance

### Next Steps:
1. Add few-shot examples (good hooks, story arcs)
2. Add examples of good short-form edits
3. Emphasize CTA requirement
4. Add platform-specific guidance (Shorts vs Reels)

## Iteration Process

1. **Baseline**: Run tests, get average score
2. **Identify issues**: Hook? Pacing? Story arc?
3. **Adjust prompt**: Edit `prompt_builder.py`
4. **Re-test**: Compare scores
5. **Iterate**: Until consistently >80/100

## Success Metrics

- **Average Score**: ≥80/100
- **Short-form Ready**: ≥80% of tests
- **Hook Effectiveness**: "good" for all
- **Pacing Score**: ≥80/100
- **Story Arc Score**: ≥80/100

## Files

- `test_dataset_short_form.json` - Test data (5 videos, 8 scenarios)
- `test_short_form_quality.py` - Quality testing framework
- `insert_test_data.py` - Database insertion script
- `PROMPT_OPTIMIZATION_GUIDE.md` - Detailed optimization guide

## Example Output

```
Testing: test_short_001 - high_energy_hype_reel
============================================================
Video duration: 38.5s
Frames: 19
Scenes: 5
Transcript segments: 10

Quality Score: 85.0/100
Short-form Ready: ✅
Coverage: 22.5%
Segments: 10
Hook: good
Pacing: 100/100
Story Arc: 100/100
Transitions: smooth
Flow: 100/100

✅ Strengths:
  - Strong hook in first 2 seconds
  - Perfect pacing for short edit
  - Story arc moments included in edit
  - Smooth transitions throughout
```

