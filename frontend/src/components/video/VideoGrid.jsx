import { motion } from 'framer-motion';
import VideoCard from './VideoCard';

export default function VideoGrid({ videos, onVideoClick, onVideoDelete, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="card p-0 overflow-hidden animate-pulse">
            <div className="aspect-video bg-dark-200" />
            <div className="p-4 space-y-3">
              <div className="h-4 bg-dark-200 rounded w-3/4" />
              <div className="h-3 bg-dark-200 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-20"
      >
        <div className="w-24 h-24 mx-auto mb-6 bg-dark-100 rounded-full flex items-center justify-center">
          <span className="text-4xl">📹</span>
        </div>
        <h3 className="text-2xl font-semibold text-dark-900 mb-2">
          No videos yet
        </h3>
        <p className="text-dark-600">
          Upload your first video to get started
        </p>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {videos.map((video, index) => (
        <motion.div
          key={video.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <VideoCard 
            video={video} 
            onClick={onVideoClick}
            onDelete={onVideoDelete}
          />
        </motion.div>
      ))}
    </div>
  );
}