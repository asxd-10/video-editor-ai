import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Filter, Upload } from 'lucide-react';
import VideoGrid from '../components/video/VideoGrid';
import Button from '../components/common/Button';
import { useVideoStore } from '../stores/videoStore';
import { videoAPI } from '../services/api';

export default function Library() {
  const navigate = useNavigate();
  const { videos, loading, fetchVideos } = useVideoStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const handleDelete = async (video) => {
    if (!confirm(`Are you sure you want to delete "${video.title}"?`)) {
      return;
    }

    try {
      await videoAPI.deleteVideo(video.id);
      // Refresh the list
      fetchVideos();
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete video');
    }
  };

  const filteredVideos = videos.filter((video) => {
    const matchesSearch = video.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || video.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 py-12">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-dark-900">Library</h1>
              <p className="text-dark-600 mt-2">
                {videos.length} {videos.length === 1 ? 'video' : 'videos'} in your library
              </p>
            </div>
            <Button
              variant="primary"
              icon={Upload}
              onClick={() => navigate('/upload')}
            >
              Upload Video
            </Button>
          </div>

          {/* Search & Filters */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-400" />
              <input
                type="text"
                placeholder="Search videos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-12"
              />
            </div>

            <div className="relative">
              <Filter size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input pl-12 pr-10 appearance-none cursor-pointer"
              >
                <option value="all">All Status</option>
                <option value="ready">Ready</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </motion.div>

        {/* Video Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <VideoGrid
            videos={filteredVideos}
            loading={loading}
            onVideoClick={(video) => navigate(`/video/${video.id}`)}
            onVideoDelete={handleDelete}
          />
        </motion.div>
      </div>
    </div>
  );
}