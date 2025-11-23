import { motion } from 'framer-motion';
import { Sparkles, Clock, Film, TrendingUp, CheckCircle2 } from 'lucide-react';
import { formatDuration } from '../../utils/formatters';
import Badge from '../common/Badge';

export default function EditPlanViewer({ plan, videoDuration }) {
  if (!plan) {
    return (
      <div className="card p-6">
        <p className="text-dark-600 text-center">No edit plan available</p>
      </div>
    );
  }

  const edl = plan.edl || [];
  const storyAnalysis = plan.story_analysis || {};
  const keyMoments = plan.key_moments || [];
  const transitions = plan.transitions || [];
  const recommendations = plan.recommendations || [];

  return (
    <div className="space-y-6">
      {/* Story Analysis */}
      {storyAnalysis && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Story Analysis</h3>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {storyAnalysis.hook_timestamp !== undefined && (
              <div className="p-3 rounded-lg bg-primary-50 border border-primary-200">
                <p className="text-xs text-primary-600 mb-1">Hook</p>
                <p className="text-lg font-bold text-primary-900">
                  {formatDuration(storyAnalysis.hook_timestamp)}
                </p>
              </div>
            )}
            {storyAnalysis.climax_timestamp !== undefined && (
              <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                <p className="text-xs text-purple-600 mb-1">Climax</p>
                <p className="text-lg font-bold text-purple-900">
                  {formatDuration(storyAnalysis.climax_timestamp)}
                </p>
              </div>
            )}
            {storyAnalysis.resolution_timestamp !== undefined && (
              <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                <p className="text-xs text-green-600 mb-1">Resolution</p>
                <p className="text-lg font-bold text-green-900">
                  {formatDuration(storyAnalysis.resolution_timestamp)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Key Moments */}
      {keyMoments.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Key Moments</h3>
          </div>
          <div className="space-y-3">
            {keyMoments.map((moment, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="p-4 rounded-lg border border-dark-200 hover:border-primary-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-dark-500">
                        {formatDuration(moment.start)} - {formatDuration(moment.end)}
                      </span>
                      <Badge
                        className={
                          moment.importance === 'high'
                            ? 'bg-red-100 text-red-700'
                            : moment.importance === 'medium'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-blue-100 text-blue-700'
                        }
                      >
                        {moment.importance}
                      </Badge>
                      {moment.story_role && (
                        <Badge className="bg-primary-100 text-primary-700">
                          {moment.story_role}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-dark-700">{moment.reason}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Decision List (EDL) */}
      {edl.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Film size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Edit Decision List</h3>
            <Badge className="bg-dark-100 text-dark-700">{edl.length} segments</Badge>
          </div>
          <div className="space-y-2">
            {edl.map((segment, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-3 rounded-lg border border-dark-200 bg-dark-50"
              >
                <div className="flex items-center gap-2 min-w-[120px]">
                  <Clock size={14} className="text-dark-500" />
                  <span className="text-xs font-mono text-dark-700">
                    {formatDuration(segment.start)} → {formatDuration(segment.end)}
                  </span>
                </div>
                <Badge
                  className={
                    segment.type === 'keep'
                      ? 'bg-green-100 text-green-700'
                      : segment.type === 'transition'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-700'
                  }
                >
                  {segment.type}
                </Badge>
                {segment.reason && (
                  <p className="text-sm text-dark-600 flex-1">{segment.reason}</p>
                )}
                {segment.transition_type && (
                  <Badge className="bg-purple-100 text-purple-700">
                    {segment.transition_type}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transitions */}
      {transitions.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Film size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Transitions</h3>
          </div>
          <div className="space-y-2">
            {transitions.map((transition, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-dark-200 bg-dark-50"
              >
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-dark-500">
                    {formatDuration(transition.from_timestamp)} → {formatDuration(transition.to_timestamp)}
                  </span>
                  <Badge className="bg-blue-100 text-blue-700">{transition.type}</Badge>
                  {transition.duration && (
                    <span className="text-xs text-dark-500">
                      ({transition.duration}s)
                    </span>
                  )}
                  {transition.reason && (
                    <p className="text-sm text-dark-600 flex-1">{transition.reason}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 size={20} className="text-primary-600" />
            <h3 className="text-lg font-semibold text-dark-900">Recommendations</h3>
          </div>
          <div className="space-y-2">
            {recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-primary-200 bg-primary-50"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={16} className="text-primary-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-dark-900">{rec.message}</p>
                    {rec.timestamp && (
                      <p className="text-xs text-dark-500 mt-1">
                        At {formatDuration(rec.timestamp)}
                      </p>
                    )}
                  </div>
                  {rec.priority && (
                    <Badge
                      className={
                        rec.priority === 'high'
                          ? 'bg-red-100 text-red-700'
                          : rec.priority === 'medium'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-blue-100 text-blue-700'
                      }
                    >
                      {rec.priority}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

