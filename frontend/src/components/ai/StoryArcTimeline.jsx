import { motion } from 'framer-motion';
import { Sparkles, Target, TrendingUp, CheckCircle2 } from 'lucide-react';
import { formatDuration } from '../../utils/formatters';

export default function StoryArcTimeline({ storyAnalysis, videoDuration, keyMoments = [] }) {
  if (!storyAnalysis || !videoDuration) {
    return null;
  }

  const hook = storyAnalysis.hook_timestamp || 0;
  const climax = storyAnalysis.climax_timestamp || videoDuration * 0.6;
  const resolution = storyAnalysis.resolution_timestamp || videoDuration;

  const getPosition = (timestamp) => (timestamp / videoDuration) * 100;

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-6">
        <Sparkles size={20} className="text-primary-600" />
        <h3 className="text-lg font-semibold text-dark-900">Story Arc Timeline</h3>
      </div>

      {/* Timeline Bar */}
      <div className="relative h-24 mb-6">
        {/* Background bar */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary-100 via-purple-100 to-green-100 rounded-full" />

        {/* Hook Marker */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2 }}
          className="absolute top-0"
          style={{ left: `${getPosition(hook)}%`, transform: 'translateX(-50%)' }}
        >
          <div className="flex flex-col items-center">
            <div className="w-4 h-4 bg-primary-500 rounded-full border-2 border-white shadow-lg" />
            <div className="mt-1 px-2 py-1 bg-primary-500 text-white text-xs rounded whitespace-nowrap">
              Hook
            </div>
          </div>
        </motion.div>

        {/* Climax Marker */}
        {climax < videoDuration && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4 }}
            className="absolute top-0"
            style={{ left: `${getPosition(climax)}%`, transform: 'translateX(-50%)' }}
          >
            <div className="flex flex-col items-center">
              <div className="w-4 h-4 bg-purple-500 rounded-full border-2 border-white shadow-lg" />
              <div className="mt-1 px-2 py-1 bg-purple-500 text-white text-xs rounded whitespace-nowrap">
                Climax
              </div>
            </div>
          </motion.div>
        )}

        {/* Resolution Marker */}
        {resolution < videoDuration && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.6 }}
            className="absolute top-0"
            style={{ left: `${getPosition(resolution)}%`, transform: 'translateX(-50%)' }}
          >
            <div className="flex flex-col items-center">
              <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow-lg" />
              <div className="mt-1 px-2 py-1 bg-green-500 text-white text-xs rounded whitespace-nowrap">
                Resolution
              </div>
            </div>
          </motion.div>
        )}

        {/* Key Moments */}
        {keyMoments.map((moment, idx) => {
          const position = getPosition(moment.start);
          return (
            <motion.div
              key={idx}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.8 + idx * 0.1 }}
              className="absolute bottom-0"
              style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
            >
              <div className="w-2 h-2 bg-yellow-500 rounded-full border border-white" />
            </motion.div>
          );
        })}

        {/* Time Labels */}
        <div className="absolute -bottom-6 left-0 right-0 flex justify-between text-xs text-dark-500">
          <span>{formatDuration(0)}</span>
          <span>{formatDuration(videoDuration)}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-primary-500 rounded-full" />
          <span className="text-dark-600">Hook</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-purple-500 rounded-full" />
          <span className="text-dark-600">Climax</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full" />
          <span className="text-dark-600">Resolution</span>
        </div>
        {keyMoments.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full" />
            <span className="text-dark-600">Key Moments</span>
          </div>
        )}
      </div>
    </div>
  );
}

