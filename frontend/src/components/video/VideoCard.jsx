import { motion } from 'framer-motion';
import { Play, Clock, Calendar, MoreVertical } from 'lucide-react';
import { formatDuration, formatRelativeTime, getStatusColor, getStatusLabel } from '../../utils/formatters';
import Badge from '../common/Badge';
import clsx from 'clsx';

export default function VideoCard({ video, onClick }) {
  const thumbnailUrl = video.thumbnail || '/placeholder-video.jpg';
  const isReady = video.status === 'ready';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -8 }}
      transition={{ duration: 0.2 }}
      onClick={() => isReady && onClick?.(video)}
      className={clsx(
        'card p-0 overflow-hidden',
        isReady && 'cursor-pointer'
      )}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-dark-100 overflow-hidden group">
        <img
          src={thumbnailUrl}
          alt={video.title}
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
        
        {/* Overlay on Hover */}
        {isReady && (
          <motion.div
            initial={{ opacity: 0 }}
            whileHover={{ opacity: 1 }}
            className="absolute inset-0 bg-black/50 flex items-center justify-center"
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-apple-xl"
            >
              <Play size={28} className="text-dark-900 ml-1" fill="currentColor" />
            </motion.div>
          </motion.div>
        )}

        {/* Duration Badge */}
        {video.duration && (
          <div className="absolute bottom-3 right-3 px-2 py-1 bg-black/80 backdrop-blur-sm rounded-lg text-white text-xs font-semibold">
            {formatDuration(video.duration)}
          </div>
        )}

        {/* Status Badge */}
        {!isReady && (
          <div className="absolute top-3 left-3">
            <Badge className={getStatusColor(video.status)}>
              {getStatusLabel(video.status)}
            </Badge>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-dark-900 text-base line-clamp-2 mb-2">
              {video.title}
            </h3>
            
            <div className="flex items-center gap-4 text-sm text-dark-600">
              {video.created_at && (
                <div className="flex items-center gap-1.5">
                  <Calendar size={14} />
                  <span>{formatRelativeTime(video.created_at)}</span>
                </div>
              )}
              
              {video.duration && (
                <div className="flex items-center gap-1.5">
                  <Clock size={14} />
                  <span>{formatDuration(video.duration)}</span>
                </div>
              )}
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-dark-100 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              // Handle menu
            }}
          >
            <MoreVertical size={18} className="text-dark-600" />
          </motion.button>
        </div>

        {video.description && (
          <p className="mt-2 text-sm text-dark-600 line-clamp-2">
            {video.description}
          </p>
        )}
      </div>
    </motion.div>
  );
}