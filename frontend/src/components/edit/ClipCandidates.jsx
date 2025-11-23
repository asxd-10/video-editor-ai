import { motion } from 'framer-motion';
import { Play, Sparkles } from 'lucide-react';
import { formatDuration } from '../../utils/formatters';
import Button from '../common/Button';
import Badge from '../common/Badge';

export default function ClipCandidates({ candidates, onSelect, onSelectClip, videoRef }) {
  const handlePlay = (candidate) => {
    if (videoRef?.current) {
      videoRef.current.currentTime = candidate.start_time;
      videoRef.current.play();
    }
  };

  if (!candidates || candidates.length === 0) {
    return (
      <div className="card p-6">
        <p className="text-dark-600 text-center">No clip candidates available</p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-dark-900">Clip Candidates</h3>
        <Badge className="bg-primary-100 text-primary-700">
          {candidates.length} clips
        </Badge>
      </div>
      <div className="space-y-3">
        {candidates.map((candidate, index) => (
          <motion.div
            key={candidate.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="p-4 rounded-lg border border-dark-200 hover:border-primary-300 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono text-dark-500">
                    {formatDuration(candidate.start_time)} - {formatDuration(candidate.end_time)}
                  </span>
                  <span className="text-xs text-dark-500">
                    ({formatDuration(candidate.duration)})
                  </span>
                </div>
                {candidate.hook_text && (
                  <p className="text-sm text-dark-700 mb-2 italic">
                    "{candidate.hook_text}"
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-dark-500">
                  <span className="flex items-center gap-1">
                    <Sparkles size={12} />
                    Score: {Math.round(candidate.score)}
                  </span>
                  {candidate.features?.strategy && (
                    <span className="px-2 py-1 bg-dark-100 rounded">
                      {candidate.features.strategy}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  icon={Play}
                  onClick={() => handlePlay(candidate)}
                >
                  Play
                </Button>
                {(onSelect || onSelectClip) && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      if (onSelectClip) onSelectClip(candidate.id);
                      if (onSelect) onSelect(candidate);
                    }}
                  >
                    Select
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

