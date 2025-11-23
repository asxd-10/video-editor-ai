import { motion } from 'framer-motion';
import { Play, Clock, Calendar } from 'lucide-react';
import { formatDuration, formatRelativeTime, getStatusColor, getStatusLabel } from '../../utils/formatters';
import Badge from '../common/Badge';
import VideoCardMenu from './VideoCardMenu';
import clsx from 'clsx';

export default function VideoCard({ video, onClick, onDelete }) {
  // Use placeholder if no thumbnail
  const thumbnailUrl = video.thumbnail 
    ? `http://localhost:8000${video.thumbnail}` 
    : 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"%3E%3Crect fill="%23e2e8f0" width="400" height="225"/%3E%3Ctext fill="%2394a3b8" font-family="sans-serif" font-size="24" dy="10.5" font-weight="bold" x="50%25" y="50%25" text-anchor="middle"%3E📹 No Thumbnail%3C/text%3E%3C/svg%3E';
  
  const isReady = video.status === 'ready';

  const handleView = () => {
    if (isReady) {
      onClick?.(video);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -8 }}
      transition={{ duration: 0.2 }}
      className="card p-0 overflow-visible"
    >
      {/* Thumbnail */}
      <div 
        className={clsx(
          "relative aspect-video bg-dark-100 overflow-hidden group",
          isReady && "cursor-pointer"
        )}
        onClick={handleView}
      >
        <img
          src={thumbnailUrl}
          alt={video.title}
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          onError={(e) => {
            // Fallback if image fails to load
            e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"%3E%3Crect fill="%23e2e8f0" width="400" height="225"/%3E%3Ctext fill="%2394a3b8" font-family="sans-serif" font-size="24" dy="10.5" font-weight="bold" x="50%25" y="50%25" text-anchor="middle"%3E📹 No Thumbnail%3C/text%3E%3C/svg%3E';
          }}
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

          {/* Three Dots Menu */}
          <VideoCardMenu
            video={video}
            onView={handleView}
            onDelete={onDelete}
          />
        </div>
      </div>
    </motion.div>
  );
}