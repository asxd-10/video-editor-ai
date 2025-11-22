import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { formatDuration } from '../../utils/formatters';

export default function TranscriptViewer({ transcript, videoRef, onSegmentClick }) {
  const containerRef = useRef(null);

  const handleSegmentClick = (startTime) => {
    if (videoRef?.current) {
      videoRef.current.currentTime = startTime;
      videoRef.current.play();
    }
    onSegmentClick?.(startTime);
  };

  if (!transcript || !transcript.segments || transcript.segments.length === 0) {
    return (
      <div className="card p-6">
        <p className="text-dark-600 text-center">No transcript available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="card p-6">
      <h3 className="text-lg font-semibold text-dark-900 mb-4">Transcript</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {transcript.segments.map((segment, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.02 }}
            className="p-3 rounded-lg hover:bg-primary-50 cursor-pointer transition-colors border border-transparent hover:border-primary-200"
            onClick={() => handleSegmentClick(segment.start)}
          >
            <div className="flex items-start gap-3">
              <span className="text-xs text-dark-500 font-mono whitespace-nowrap mt-1">
                {formatDuration(segment.start)}
              </span>
              <p className="text-sm text-dark-700 flex-1">{segment.text}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

