import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Download, Trash2, Clock, Calendar, FileVideo } from 'lucide-react';
import VideoPlayer from '../components/video/VideoPlayer';
import ProcessingStatus from '../components/video/ProcessingStatus';
import TranscriptViewer from '../components/edit/TranscriptViewer';
import ClipCandidates from '../components/edit/ClipCandidates';
import AIActions from '../components/edit/AIActions';
import EditJobManager from '../components/edit/EditJobManager';
import AnalysisInsights from '../components/edit/AnalysisInsights';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import { videoAPI } from '../services/api';
import { formatFileSize, formatDuration, formatDate, getStatusColor, getStatusLabel } from '../utils/formatters';

export default function VideoView() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [video, setVideo] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [transcript, setTranscript] = useState(null);
  const [transcriptStatus, setTranscriptStatus] = useState('not_found');
  const [candidates, setCandidates] = useState([]);
  const [analysisStatus, setAnalysisStatus] = useState('not_found');
  const [selectedClipId, setSelectedClipId] = useState(null);

  useEffect(() => {
    loadVideo();
    loadLogs();
    loadTranscriptStatus();
    loadCandidates();
  }, [videoId]);

  // Poll for transcript status
  useEffect(() => {
    if (transcriptStatus === 'queued') {
      const interval = setInterval(() => {
        loadTranscriptStatus();
      }, 5000); // Check every 5 seconds
      return () => clearInterval(interval);
    }
  }, [transcriptStatus]);

  const loadVideo = async () => {
    try {
      const response = await videoAPI.getVideo(videoId);
      setVideo(response.data);
      // Update analysis status if metadata exists
      // analysis_metadata might be a string (JSON) or an object
      let analysisMetadata = response.data.analysis_metadata;
      if (typeof analysisMetadata === 'string') {
        try {
          analysisMetadata = JSON.parse(analysisMetadata);
        } catch (e) {
          console.warn('Failed to parse analysis_metadata:', e);
          analysisMetadata = null;
        }
      }
      
      if (analysisMetadata && 
          (analysisMetadata.silence_segments || 
           analysisMetadata.scene_timestamps)) {
        setAnalysisStatus('complete');
      } else {
        setAnalysisStatus('not_found');
      }
    } catch (error) {
      console.error('Failed to load video:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      const response = await videoAPI.getLogs(videoId);
      setLogs(response.data.logs);
    } catch (error) {
      console.error('Failed to load logs:', error);
    }
  };

  const loadTranscriptStatus = async () => {
    try {
      const response = await videoAPI.getTranscriptStatus(videoId);
      setTranscriptStatus(response.data.status);
      if (response.data.status === 'complete') {
        loadTranscript();
      }
    } catch (error) {
      console.error('Failed to load transcript status:', error);
      setTranscriptStatus('not_found');
    }
  };

  const loadTranscript = async () => {
    try {
      const response = await videoAPI.getTranscript(videoId);
      setTranscript(response.data);
    } catch (error) {
      console.error('Failed to load transcript:', error);
    }
  };

  const loadCandidates = async () => {
    try {
      const response = await videoAPI.getCandidates(videoId);
      setCandidates(response.data.candidates || []);
    } catch (error) {
      // Any error means no candidates available - this is fine, just set empty
      setCandidates([]);
    }
  };

  const handleTranscribe = async () => {
    try {
      await videoAPI.startTranscription(videoId);
      setTranscriptStatus('queued');
    } catch (error) {
      console.error('Failed to start transcription:', error);
      alert('Failed to start transcription');
    }
  };

  const handleAnalyze = async () => {
    try {
      await videoAPI.startAnalysis(videoId);
      setAnalysisStatus('queued');
      // Poll for completion by checking video metadata
      const interval = setInterval(async () => {
        try {
          const response = await videoAPI.getVideo(videoId);
          // Parse analysis_metadata if it's a string
          let analysisMetadata = response.data.analysis_metadata;
          if (typeof analysisMetadata === 'string') {
            try {
              analysisMetadata = JSON.parse(analysisMetadata);
            } catch (e) {
              // Not valid JSON yet, keep polling
              return;
            }
          }
          
          if (analysisMetadata && 
              (analysisMetadata.silence_segments || 
               analysisMetadata.scene_timestamps)) {
            setAnalysisStatus('complete');
            setVideo(response.data); // Update video state
            clearInterval(interval);
          }
        } catch (e) {
          // Ignore errors while polling
        }
      }, 5000);
      
      // Cleanup interval after 5 minutes (safety)
      setTimeout(() => clearInterval(interval), 5 * 60 * 1000);
    } catch (error) {
      console.error('Failed to start analysis:', error);
      alert('Failed to start analysis');
      setAnalysisStatus('not_found');
    }
  };

  const handleGenerateCandidates = async () => {
    try {
      await videoAPI.generateCandidates(videoId);
      await loadCandidates();
    } catch (error) {
      console.error('Failed to generate candidates:', error);
      alert('Failed to generate candidates');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this video?')) return;

    try {
      await videoAPI.deleteVideo(videoId);
      navigate('/library');
    } catch (error) {
      console.error('Failed to delete video:', error);
      alert('Failed to delete video');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-dark-900 mb-2">Video not found</h2>
          <Button onClick={() => navigate('/library')}>Back to Library</Button>
        </div>
      </div>
    );
  }

  const proxyUrl = video.assets?.proxy_720p?.url;
  const thumbnailUrl = video.thumbnails?.[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 py-12">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Button
            variant="ghost"
            icon={ArrowLeft}
            onClick={() => navigate('/library')}
            className="mb-4"
          >
            Back to Library
          </Button>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Player */}
            {video.status === 'ready' && proxyUrl && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <VideoPlayer
                  ref={videoRef}
                  src={`http://localhost:8000${proxyUrl}`}
                  poster={thumbnailUrl ? `http://localhost:8000${thumbnailUrl}` : undefined}
                  className="w-full aspect-video"
                />
              </motion.div>
            )}

            {/* AI Actions */}
            {video.status === 'ready' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <AIActions
                  videoId={videoId}
                  onTranscribe={handleTranscribe}
                  onAnalyze={handleAnalyze}
                  onGenerateCandidates={handleGenerateCandidates}
                  transcriptStatus={transcriptStatus}
                  analysisStatus={analysisStatus}
                />
              </motion.div>
            )}

            {/* Transcript Viewer */}
            {transcript && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <TranscriptViewer
                  transcript={transcript}
                  videoRef={videoRef}
                />
              </motion.div>
            )}

            {/* Clip Candidates - Optional, only show if they exist */}
            {candidates.length > 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <ClipCandidates
                  candidates={candidates}
                  videoRef={videoRef}
                  onSelectClip={setSelectedClipId}
                />
              </motion.div>
            ) : transcriptStatus === 'complete' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="card p-6"
              >
                <p className="text-dark-600 text-center">
                  No clip candidates yet. Click "Generate" in AI Features to create them.
                </p>
              </motion.div>
            )}

            {/* Analysis Insights */}
            {video.status === 'ready' && analysisStatus === 'complete' && video.analysis_metadata && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <AnalysisInsights 
                  analysisMetadata={video.analysis_metadata}
                  videoDuration={video.duration_seconds}
                />
              </motion.div>
            )}

            {/* Edit Job Manager - Always show, but enable only when video is ready */}
            {video.status === 'ready' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <EditJobManager
                  videoId={videoId}
                  clipCandidateId={selectedClipId || null}
                  hasAnalysis={analysisStatus === 'complete'}
                  analysisMetadata={video.analysis_metadata}
                  videoDuration={video.duration_seconds}
                  onEditComplete={(jobId) => {
                    console.log('Edit job completed:', jobId);
                    // Optionally reload or show notification
                  }}
                />
              </motion.div>
            )}

            {/* Video Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h1 className="text-3xl font-bold text-dark-900 mb-2">
                    {video.title}
                  </h1>
                  <Badge className={getStatusColor(video.status)}>
                    {getStatusLabel(video.status)}
                  </Badge>
                </div>
              </div>

              {video.description && (
                <p className="text-dark-700 mt-4 leading-relaxed">
                  {video.description}
                </p>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-dark-200">
                {video.duration && (
                  <div>
                    <div className="flex items-center gap-2 text-dark-600 mb-1">
                      <Clock size={16} />
                      <span className="text-sm">Duration</span>
                    </div>
                    <p className="font-semibold text-dark-900">
                      {formatDuration(video.duration)}
                    </p>
                  </div>
                )}

                {video.resolution && (
                  <div>
                    <div className="flex items-center gap-2 text-dark-600 mb-1">
                      <FileVideo size={16} />
                      <span className="text-sm">Resolution</span>
                    </div>
                    <p className="font-semibold text-dark-900">
                      {video.resolution}
                    </p>
                  </div>
                )}

                {video.file_size && (
                  <div>
                    <div className="text-dark-600 mb-1 text-sm">File Size</div>
                    <p className="font-semibold text-dark-900">
                      {formatFileSize(video.file_size)}
                    </p>
                  </div>
                )}

                {video.created_at && (
                  <div>
                    <div className="flex items-center gap-2 text-dark-600 mb-1">
                      <Calendar size={16} />
                      <span className="text-sm">Uploaded</span>
                    </div>
                    <p className="font-semibold text-dark-900">
                      {formatDate(video.created_at)}
                    </p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-dark-200">
                {video.status === 'ready' && proxyUrl && (
                  <Button
                    variant="primary"
                    icon={Download}
                    onClick={() => window.open(`http://localhost:8000${proxyUrl}`, '_blank')}
                  >
                    Download
                  </Button>
                )}
                <Button
                  variant="danger"
                  icon={Trash2}
                  onClick={handleDelete}
                >
                  Delete
                </Button>
              </div>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Processing Status */}
            {logs.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <ProcessingStatus logs={logs} />
              </motion.div>
            )}

            {/* Thumbnails */}
            {video.thumbnails && video.thumbnails.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="card p-6"
              >
                <h3 className="text-lg font-semibold text-dark-900 mb-4">
                  Thumbnails
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {video.thumbnails.map((thumb, index) => (
                    <img
                      key={index}
                      src={`http://localhost:8000${thumb}`}
                      alt={`Thumbnail ${index + 1}`}
                      className="w-full aspect-video object-cover rounded-lg border border-dark-200"
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}