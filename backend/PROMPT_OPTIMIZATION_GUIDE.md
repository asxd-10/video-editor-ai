# Prompt Optimization Guide for Short-Form Content

## Goal
Optimize LLM prompts to create **awesome short-form edits** (Shorts/Reels) that:
- Hook viewers in first 2 seconds
- Maintain engagement throughout
- Follow story arc effectively
- Have smooth transitions
- Meet influencer/shorts/reels standards
- Are 40 seconds or less

## Evaluation Criteria

### 1. Hook Effectiveness (Critical for Shorts/Reels)
- **Good**: Hook starts in first 2 seconds, substantial (≥1.5s)
- **Weak**: Hook too short or starts late
- **Impact**: First 2 seconds determine if viewer watches or skips

### 2. Pacing
- **Short edit**: 15-30% coverage (aggressive cutting)
- **Medium edit**: 50-70% coverage (balanced)
- **Long edit**: 70-90% coverage (preserve most content)

### 3. Story Arc
- Hook, Build, Climax, Resolution must be present
- Timestamps should align with EDL segments
- Arc should be clear and engaging

### 4. Transitions
- Smooth: Gaps <0.5s (seamless)
- Mostly smooth: 1-2 gaps >3s (acceptable)
- Choppy: Many gaps >3s (needs improvement)

### 5. Flow
- Chronological order (unless intentional flashback)
- Not too many very short segments (<1s)
- Logical sequence

### 6. Short-Form Specific
- Total duration ≤40 seconds
- Fast-paced (for short edits)
- High energy (for hype reels)
- Clear CTA at end

## Test Dataset

### Videos Included:
1. **Travel vlog** (38.5s) - Multiple scenarios
2. **Product review** (35.0s) - Quick review
3. **Day in life** (28.0s) - Lifestyle content
4. **Cooking tutorial** (25.0s) - Quick recipe
5. **Fitness workout** (32.0s) - Exercise routine
6. **Edge cases**: Very short (15s), Maximum length (40s)

### Scenarios Tested:
- High energy hype reel
- Nostalgic summer vibes
- Quick tips tutorial
- Aesthetic lifestyle
- Motivational workout

## Prompt Tuning Process

### Step 1: Baseline Test
```bash
# Insert test data
python insert_test_data.py test_dataset_short_form.json

# Run tests
python test_short_form_quality.py test_dataset_short_form.json
```

### Step 2: Analyze Results
Look for patterns:
- **Hook issues**: Adjust prompt to emphasize first 2 seconds
- **Pacing issues**: Adjust desired_length instructions
- **Story arc issues**: Strengthen story_arc requirements
- **Transition issues**: Add transition guidance

### Step 3: Iterate Prompt
Edit `prompt_builder.py`:
- Add examples of good hooks
- Emphasize short-form requirements
- Add few-shot examples
- Strengthen story arc instructions

### Step 4: Re-test
```bash
python test_short_form_quality.py test_dataset_short_form.json
```

### Step 5: Compare Scores
- Before: Average score X/100
- After: Average score Y/100
- Target: >80/100 for short-form ready

## Few-Shot Prompt Examples

### Good Hook Examples:
```
HOOK EXAMPLES (First 2 seconds):
- Travel: Most exciting moment (surfing, jumping, epic view)
- Product: Product reveal or key feature demo
- Tutorial: Final result or most impressive step
- Fitness: Best move or results preview
```

### Good Story Arc Examples:
```
STORY ARC EXAMPLES:
- Short (15-30% coverage):
  Hook (0-2s): Most exciting moment
  Build (2-15s): Rapid highlights
  Climax (15-20s): Best moment
  Resolution (20-30s): CTA

- Medium (50-70% coverage):
  Hook (0-3s): Engaging opening
  Build (3-20s): Story development
  Climax (20-25s): Peak moment
  Resolution (25-35s): Conclusion
```

## Key Prompt Adjustments

### For Short-Form Content:
1. **Emphasize hook**: "CRITICAL: Hook must start in first 2 seconds"
2. **Fast pacing**: "For 'short' edits, aggressively cut to 15-30% of original"
3. **High energy**: "Maintain high energy, fast cuts, dynamic transitions"
4. **Clear CTA**: "Always end with clear call-to-action"
5. **40s limit**: "Final edit must be ≤40 seconds"

### For Story Arc:
1. **Hook requirement**: "Hook timestamp must be in first 2 seconds"
2. **Climax placement**: "Climax should be at 60-80% of edit duration"
3. **Resolution**: "Resolution should include CTA or emotional closure"

## Success Metrics

### Target Scores:
- **Hook Effectiveness**: "good" (100%)
- **Pacing Score**: 80-100/100
- **Story Arc Score**: 80-100/100
- **Transition Quality**: "smooth" or "mostly_smooth"
- **Flow Score**: 80-100/100
- **Overall Score**: ≥80/100
- **Short-form Ready**: Yes

### Red Flags:
- Hook starts >2s
- Coverage mismatch (short edit but >40%)
- Story arc moments missing
- Many large gaps (>3s)
- Total duration >40s

## Iteration Checklist

After each prompt change:
- [ ] Run full test suite
- [ ] Check average score improved
- [ ] Verify hook effectiveness
- [ ] Verify pacing matches desired_length
- [ ] Verify story arc is followed
- [ ] Check transitions are smooth
- [ ] Verify all edits ≤40s
- [ ] Review EDL manually (watch the logic)

## Next Steps

1. **Insert test data** → `python insert_test_data.py test_dataset_short_form.json`
2. **Run baseline tests** → `python test_short_form_quality.py test_dataset_short_form.json`
3. **Review scores** → Identify patterns
4. **Adjust prompts** → Edit `prompt_builder.py`
5. **Re-test** → Compare scores
6. **Iterate** → Until scores are consistently >80/100

## Example Prompt Enhancement

### Current:
"Create a storytelling edit plan..."

### Enhanced (for short-form):
"Create a SHORT-FORM storytelling edit (≤40s) optimized for Shorts/Reels:

CRITICAL REQUIREMENTS:
1. HOOK: Must start in first 2 seconds with most engaging moment
2. PACING: For 'short' edits, cut to 15-30% coverage (aggressive)
3. STORY ARC: Hook → Build → Climax → Resolution (all must be in EDL)
4. TRANSITIONS: Minimize gaps >3s, prefer smooth flow
5. DURATION: Final edit must be ≤40 seconds

TARGET AUDIENCE: Influencers creating Shorts/Reels
QUALITY STANDARD: Must be engaging enough to prevent skipping"

