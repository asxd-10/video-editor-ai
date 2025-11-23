import { Info, Clock, Film } from 'lucide-react';
import { formatDuration } from '../../utils/formatters';

export default function AnalysisInsights({ analysisMetadata, videoDuration }) {
  if (!analysisMetadata) return null;

  // Parse if string
  let metadata = analysisMetadata;
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata);
    } catch (e) {
      return null;
    }
  }

  const silenceSegments = metadata.silence_segments || [];
  const sceneTimestamps = metadata.scene_timestamps || [];

  // Calculate total silence time
  const totalSilenceTime = silenceSegments.reduce((total, seg) => {
    const [start, end] = Array.isArray(seg) ? seg : [seg.start, seg.end];
    return total + (end - start);
  }, 0);

  const silencePercentage = videoDuration > 0 
    ? ((totalSilenceTime / videoDuration) * 100).toFixed(1)
    : 0;

  const insights = [];

  // Silence insights
  if (silenceSegments.length > 0) {
    insights.push({
      icon: Clock,
      label: 'Silence Detected',
      value: `${silenceSegments.length} segments`,
      detail: `${formatDuration(totalSilenceTime)} total (${silencePercentage}%)`,
      color: 'text-blue-600'
    });
  }

  // Scene insights
  if (sceneTimestamps.length > 0) {
    insights.push({
      icon: Film,
      label: 'Scene Changes',
      value: `${sceneTimestamps.length} cuts`,
      detail: 'Major visual transitions detected',
      color: 'text-purple-600'
    });
  }

  if (insights.length === 0) return null;

  return (
    <div className="card p-4 bg-gradient-to-br from-blue-50 to-purple-50 border border-blue-200">
      <div className="flex items-center gap-2 mb-3">
        <Info size={18} className="text-blue-600" />
        <h4 className="text-sm font-semibold text-dark-900">Analysis Insights</h4>
      </div>
      <div className="space-y-2">
        {insights.map((insight, idx) => {
          const Icon = insight.icon;
          return (
            <div key={idx} className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2 flex-1">
                <Icon size={16} className={`${insight.color} mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-dark-700">{insight.label}</div>
                  <div className="text-xs text-dark-500">{insight.detail}</div>
                </div>
              </div>
              <div className="text-xs font-semibold text-dark-900">{insight.value}</div>
            </div>
          );
        })}
      </div>
      {silenceSegments.length > 0 && (
        <div className="mt-3 pt-3 border-t border-blue-200">
          <p className="text-xs text-dark-600">
            💡 <strong>Tip:</strong> Enable "Remove Silence" to automatically cut out {silenceSegments.length} silence gaps and save {formatDuration(totalSilenceTime)} of video time.
          </p>
        </div>
      )}
    </div>
  );
}

