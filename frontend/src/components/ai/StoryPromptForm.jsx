import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Target, MessageSquare, Film } from 'lucide-react';
import Button from '../common/Button';

const TONE_OPTIONS = [
  { value: 'educational', label: 'Educational' },
  { value: 'entertaining', label: 'Entertaining' },
  { value: 'dramatic', label: 'Dramatic' },
  { value: 'inspirational', label: 'Inspirational' },
  { value: 'casual', label: 'Casual' },
];

const AUDIENCE_OPTIONS = [
  { value: 'general', label: 'General Audience' },
  { value: 'students', label: 'Students' },
  { value: 'professionals', label: 'Professionals' },
  { value: 'creators', label: 'Content Creators' },
];

// Percentage-based length options
const LENGTH_PRESETS = [
  { percentage: 30, label: 'Short (30%)', description: '1/4 to 1/3 of original' },
  { percentage: 50, label: 'Medium (50%)', description: 'About half of original' },
  { percentage: 85, label: 'Long (85%)', description: '70-100% of original' },
];

export default function StoryPromptForm({ onSubmit, initialData, loading }) {
  const [formData, setFormData] = useState({
    target_audience: initialData?.target_audience || 'general',
    story_arc: {
      hook: initialData?.story_arc?.hook || 'Grab attention in first 3 seconds',
      build: initialData?.story_arc?.build || 'Build interest and context',
      climax: initialData?.story_arc?.climax || 'Main point/revelation',
      resolution: initialData?.story_arc?.resolution || 'Conclusion/call-to-action',
    },
    tone: initialData?.tone || 'educational',
    key_message: initialData?.key_message || '',
    desired_length_percentage: initialData?.desired_length_percentage || 50.0,
    style_preferences: {
      pacing: initialData?.style_preferences?.pacing || 'moderate',
      transitions: initialData?.style_preferences?.transitions || 'smooth',
      emphasis: initialData?.style_preferences?.emphasis || 'balanced',
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Target Audience */}
      <div>
        <label className="flex items-center gap-2 text-sm font-semibold text-dark-900 mb-2">
          <Target size={16} className="text-primary-600" />
          Target Audience
        </label>
        <div className="grid grid-cols-2 gap-2">
          {AUDIENCE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFormData({ ...formData, target_audience: option.value })}
              className={`px-4 py-2 rounded-lg border transition-all text-sm ${
                formData.target_audience === option.value
                  ? 'bg-primary-500 text-white border-primary-500'
                  : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tone */}
      <div>
        <label className="flex items-center gap-2 text-sm font-semibold text-dark-900 mb-2">
          <Film size={16} className="text-primary-600" />
          Tone
        </label>
        <div className="grid grid-cols-3 gap-2">
          {TONE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFormData({ ...formData, tone: option.value })}
              className={`px-4 py-2 rounded-lg border transition-all text-sm ${
                formData.tone === option.value
                  ? 'bg-primary-500 text-white border-primary-500'
                  : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Key Message */}
      <div>
        <label className="flex items-center gap-2 text-sm font-semibold text-dark-900 mb-2">
          <MessageSquare size={16} className="text-primary-600" />
          Key Message
        </label>
        <textarea
          value={formData.key_message}
          onChange={(e) => setFormData({ ...formData, key_message: e.target.value })}
          placeholder="What's the main takeaway for viewers?"
          className="w-full px-4 py-3 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none resize-none"
          rows={3}
        />
      </div>

      {/* Story Arc */}
      <div>
        <label className="flex items-center gap-2 text-sm font-semibold text-dark-900 mb-2">
          <Sparkles size={16} className="text-primary-600" />
          Story Arc
        </label>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Hook</label>
            <input
              type="text"
              value={formData.story_arc.hook}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  story_arc: { ...formData.story_arc, hook: e.target.value },
                })
              }
              placeholder="Grab attention in first 3 seconds"
              className="w-full px-3 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Build</label>
            <input
              type="text"
              value={formData.story_arc.build}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  story_arc: { ...formData.story_arc, build: e.target.value },
                })
              }
              placeholder="Build interest and context"
              className="w-full px-3 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Climax</label>
            <input
              type="text"
              value={formData.story_arc.climax}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  story_arc: { ...formData.story_arc, climax: e.target.value },
                })
              }
              placeholder="Main point/revelation"
              className="w-full px-3 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Resolution</label>
            <input
              type="text"
              value={formData.story_arc.resolution}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  story_arc: { ...formData.story_arc, resolution: e.target.value },
                })
              }
              placeholder="Conclusion/call-to-action"
              className="w-full px-3 py-2 rounded-lg border border-dark-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none text-sm"
            />
          </div>
        </div>
      </div>

      {/* Desired Length Percentage */}
      <div>
        <label className="text-sm font-semibold text-dark-900 mb-2 block">
          Desired Length: {formData.desired_length_percentage}% of original video
        </label>
        <div className="space-y-3">
          {/* Percentage Slider */}
          <div className="relative">
            <input
              type="range"
              min="25"
              max="100"
              step="5"
              value={formData.desired_length_percentage}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  desired_length_percentage: parseFloat(e.target.value),
                })
              }
              className="w-full h-2 bg-dark-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <div className="flex justify-between text-xs text-dark-500 mt-1">
              <span>25%</span>
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>
          
          {/* Quick Presets */}
          <div className="flex gap-2">
            {LENGTH_PRESETS.map((preset) => (
              <button
                key={preset.percentage}
                type="button"
                onClick={() =>
                  setFormData({
                    ...formData,
                    desired_length_percentage: preset.percentage,
                  })
                }
                className={`px-3 py-1.5 rounded-lg border transition-all text-xs flex-1 ${
                  Math.abs(formData.desired_length_percentage - preset.percentage) < 5
                    ? 'bg-primary-500 text-white border-primary-500'
                    : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
                }`}
                title={preset.description}
              >
                {preset.label}
              </button>
            ))}
          </div>
          
          {/* Description */}
          <p className="text-xs text-dark-500">
            {formData.desired_length_percentage <= 33
              ? 'Short: Fast-paced, rapid cuts (1/4 to 1/3 of original)'
              : formData.desired_length_percentage <= 60
              ? 'Medium: Balanced pacing (about half of original)'
              : 'Long: Preserve most content (70-100% of original)'}
          </p>
        </div>
      </div>

      {/* Style Preferences */}
      <div>
        <label className="text-sm font-semibold text-dark-900 mb-2 block">Style Preferences</label>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Pacing</label>
            <div className="flex gap-2">
              {['slow', 'moderate', 'fast'].map((pace) => (
                <button
                  key={pace}
                  type="button"
                  onClick={() =>
                    setFormData({
                      ...formData,
                      style_preferences: { ...formData.style_preferences, pacing: pace },
                    })
                  }
                  className={`px-4 py-2 rounded-lg border transition-all text-sm capitalize ${
                    formData.style_preferences.pacing === pace
                      ? 'bg-primary-500 text-white border-primary-500'
                      : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
                  }`}
                >
                  {pace}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-dark-600 mb-1 block">Transitions</label>
            <div className="flex gap-2">
              {['minimal', 'smooth', 'dynamic'].map((trans) => (
                <button
                  key={trans}
                  type="button"
                  onClick={() =>
                    setFormData({
                      ...formData,
                      style_preferences: { ...formData.style_preferences, transitions: trans },
                    })
                  }
                  className={`px-4 py-2 rounded-lg border transition-all text-sm capitalize ${
                    formData.style_preferences.transitions === trans
                      ? 'bg-primary-500 text-white border-primary-500'
                      : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
                  }`}
                >
                  {trans}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <Button
        type="submit"
        variant="primary"
        icon={Sparkles}
        disabled={loading}
        className="w-full"
      >
        {loading ? 'Generating Edit Plan...' : 'Generate AI Edit Plan'}
      </Button>
    </form>
  );
}

