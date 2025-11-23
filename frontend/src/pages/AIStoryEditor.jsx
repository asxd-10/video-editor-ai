import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Loader2, CheckCircle2, XCircle, Download, Film, Video, Plus, X } from 'lucide-react';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import StoryPromptForm from '../components/ai/StoryPromptForm';
import SummaryEditor from '../components/ai/SummaryEditor';
import EditPlanViewer from '../components/ai/EditPlanViewer';
import StoryArcTimeline from '../components/ai/StoryArcTimeline';
import VideoPlayer from '../components/video/VideoPlayer';
import { videoAPI } from '../services/api';
import { formatDuration } from '../utils/formatters';

const ASPECT_RATIOS = [
  { value: '16:9', label: 'YouTube (16:9)', icon: '📺' },
  { value: '9:16', label: 'TikTok/Reels (9:16)', icon: '📱' },
  { value: '1:1', label: 'Instagram (1:1)', icon: '📸' },
];

export default function AIStoryEditor() {
  const { videoId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [currentJob, setCurrentJob] = useState(null);
  const [editJobs, setEditJobs] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [selectedAspectRatios, setSelectedAspectRatios] = useState(['16:9']);
  const [editJobId, setEditJobId] = useState(null);
  const [editJobStatus, setEditJobStatus] = useState(null);
  const [originalVideoUrl, setOriginalVideoUrl] = useState(null);
  const [selectedVideoIds, setSelectedVideoIds] = useState([videoId]); // Multi-video support
  const [availableVideos, setAvailableVideos] = useState([]);
  const [showVideoSelector, setShowVideoSelector] = useState(false);

  useEffect(() => {
    loadData();
    loadJobs();
    loadAvailableVideos();
  }, [videoId]);
  
  const loadAvailableVideos = async () => {
    try {
      const response = await videoAPI.listVideos();
      setAvailableVideos(response.data.videos || []);
    } catch (error) {
      console.error('Failed to load videos:', error);
    }
  };

  // Auto-populate with test data in development
  useEffect(() => {
    if (import.meta.env.DEV && data && !summary) {
      // Auto-populate summary after data loads
      setSummary({
        video_summary: "A video showcasing a driving simulator setup at a university center, featuring VR technology and racing equipment.",
        key_moments: [
          "VR headset interaction",
          "Racing simulator demonstration",
          "University center showcase"
        ],
        content_type: "demonstration",
        main_topics: ["technology", "gaming", "university"],
        speaker_style: "casual"
      });
    }
  }, [data]);

  // Poll for AI edit job updates
  useEffect(() => {
    if (!currentJob || currentJob.status === 'completed' || currentJob.status === 'failed') {
      return;
    }

    const interval = setInterval(() => {
      if (currentJob) {
        loadJobStatus(currentJob.job_id);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [currentJob]);

  // Poll for EditJob status (after applying AI edit)
  useEffect(() => {
    if (!editJobId || !editJobStatus || editJobStatus.status === 'completed' || editJobStatus.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const response = await videoAPI.getEditJob(videoId, editJobId);
        setEditJobStatus(response.data);
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to poll edit job status:', error);
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [editJobId, editJobStatus, videoId]);

  const loadData = async () => {
    try {
      const response = await videoAPI.getAIEditData(videoId);
      setData(response.data);
      
      // Get original video URL from media
      const media = response.data.media;
      if (media) {
        // Prioritize video_url (S3), fallback to original_path
        const videoUrl = media.video_url || media.original_path;
        if (videoUrl) {
          // If it's already a full URL (S3), use it directly
          // If it's a relative path, convert to API URL
          if (videoUrl.startsWith('http://') || videoUrl.startsWith('https://')) {
            setOriginalVideoUrl(videoUrl);
          } else {
            // Relative path - construct API URL
            const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            setOriginalVideoUrl(`${apiBase}${videoUrl.startsWith('/') ? '' : '/'}${videoUrl}`);
          }
        } else {
          setOriginalVideoUrl(null);
        }
      }
      
      // Initialize summary from data or use defaults
      if (response.data.summary) {
        setSummary(response.data.summary);
      } else {
        setSummary({
          video_summary: '',
          key_moments: [],
          content_type: 'presentation',
          main_topics: [],
          speaker_style: 'casual',
        });
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async () => {
    try {
      const response = await videoAPI.listAIEditJobs(videoId);
      setEditJobs(response.data.jobs || []);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    }
  };

  const loadJobStatus = async (jobId) => {
    try {
      const response = await videoAPI.getAIEditPlan(videoId, jobId);
      setCurrentJob(response.data);
      
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        loadJobs(); // Reload jobs list
      }
    } catch (error) {
      console.error('Failed to load job status:', error);
    }
  };

  const handleGenerate = async (storyPrompt) => {
    setGenerating(true);
    try {
      // Use selectedVideoIds (multi-video support)
      const videoIdsToUse = selectedVideoIds.length > 1 ? selectedVideoIds : undefined;
      const response = await videoAPI.generateAIEdit(videoId, {
        summary: summary,
        story_prompt: storyPrompt,
        video_ids: videoIdsToUse, // Send multiple video IDs if more than one selected
      });

      const jobId = response.data.job_id;
      setCurrentJob({
        job_id: jobId,
        status: 'queued',
      });

      // Start polling
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await videoAPI.getAIEditPlan(videoId, jobId);
          setCurrentJob(statusResponse.data);

          if (
            statusResponse.data.status === 'completed' ||
            statusResponse.data.status === 'failed'
          ) {
            clearInterval(pollInterval);
            loadJobs();
          }
        } catch (error) {
          console.error('Polling error:', error);
          clearInterval(pollInterval);
        }
      }, 3000);
    } catch (error) {
      console.error('Failed to generate edit:', error);
      alert('Failed to generate edit plan. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleApply = async () => {
    if (!currentJob || currentJob.status !== 'completed') {
      alert('Please wait for the edit plan to complete first.');
      return;
    }

    setApplying(true);
    try {
      const response = await videoAPI.applyAIEdit(videoId, currentJob.job_id, selectedAspectRatios);
      
      // Store the EditJob ID for polling
      const newEditJobId = response.data.edit_job_id;
      setEditJobId(newEditJobId);
      
      // Start polling for EditJob status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await videoAPI.getEditJob(videoId, newEditJobId);
          setEditJobStatus(statusResponse.data);
          
          if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
            clearInterval(pollInterval);
            setApplying(false);
          }
        } catch (error) {
          console.error('Polling error:', error);
          clearInterval(pollInterval);
          setApplying(false);
        }
      }, 3000);
      
      // Initial status load
      const initialStatus = await videoAPI.getEditJob(videoId, newEditJobId);
      setEditJobStatus(initialStatus.data);
      
    } catch (error) {
      console.error('Failed to apply edit:', error);
      alert('Failed to apply edit. Please try again.');
      setApplying(false);
    }
  };

  const handleDownload = async (jobId, aspectRatio) => {
    try {
      const response = await videoAPI.applyAIEdit(videoId, jobId, [aspectRatio]);
      
      // The response should have output_paths, but for download we need to construct URL
      // For now, show a message - we'll need to add a download endpoint
      alert('Download feature coming soon! The video is being rendered.');
    } catch (error) {
      console.error('Failed to download:', error);
      alert('Failed to download video. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-dark-600">Loading AI Editor...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load video data</p>
          <Button onClick={() => navigate('/library')}>Back to Library</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 py-12">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Button
            variant="ghost"
            icon={ArrowLeft}
            onClick={() => navigate(`/video/${videoId}`)}
            className="mb-4"
          >
            Back to Video
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-dark-900 mb-2">AI Storytelling Editor</h1>
              <p className="text-dark-600">
                Create narrative-driven edits using AI. Video ID: <code className="text-xs bg-dark-100 px-2 py-1 rounded">{videoId}</code>
              </p>
            </div>
            <Badge className="bg-primary-100 text-primary-700">
              {data.frames?.count || 0} frames • {formatDuration(data.video_duration || 0)}
            </Badge>
          </div>
        </motion.div>

        {/* Multi-Video Selector */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 card p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-dark-700">
              Videos to Edit {selectedVideoIds.length > 1 && `(${selectedVideoIds.length} selected)`}
            </label>
            <button
              onClick={() => setShowVideoSelector(!showVideoSelector)}
              className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1"
            >
              <Plus size={14} />
              {showVideoSelector ? 'Hide' : 'Add Videos'}
            </button>
          </div>
          
          {/* Selected Videos */}
          <div className="flex flex-wrap gap-2 mb-3">
            {selectedVideoIds.map((vidId) => {
              const video = availableVideos.find(v => v.id === vidId) || { id: vidId, title: vidId };
              return (
                <Badge
                  key={vidId}
                  className="bg-primary-100 text-primary-700 flex items-center gap-1"
                >
                  {video.title || vidId}
                  {vidId !== videoId && (
                    <button
                      onClick={() => setSelectedVideoIds(selectedVideoIds.filter(id => id !== vidId))}
                      className="ml-1 hover:text-primary-900"
                    >
                      <X size={12} />
                    </button>
                  )}
                </Badge>
              );
            })}
          </div>

          {/* Video Selector Dropdown */}
          {showVideoSelector && (
            <div className="border border-dark-200 rounded-lg p-3 bg-white max-h-48 overflow-y-auto">
              <div className="space-y-2">
                {availableVideos
                  .filter(v => !selectedVideoIds.includes(v.id))
                  .map((video) => (
                    <button
                      key={video.id}
                      onClick={() => setSelectedVideoIds([...selectedVideoIds, video.id])}
                      className="w-full text-left px-3 py-2 rounded hover:bg-primary-50 text-sm text-dark-700 flex items-center justify-between"
                    >
                      <span>{video.title || video.id}</span>
                      <Plus size={14} className="text-primary-600" />
                    </button>
                  ))}
                {availableVideos.filter(v => !selectedVideoIds.includes(v.id)).length === 0 && (
                  <p className="text-sm text-dark-500 text-center py-2">All videos selected</p>
                )}
              </div>
            </div>
          )}
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Forms */}
          <div className="lg:col-span-2 space-y-6">
            {/* Summary Editor */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <SummaryEditor
                summary={summary}
                onSave={setSummary}
                loading={generating}
              />
            </motion.div>

            {/* Story Prompt Form */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card p-6"
            >
              <div className="flex items-center gap-2 mb-6">
                <Film size={20} className="text-primary-600" />
                <h2 className="text-xl font-semibold text-dark-900">Story Prompt</h2>
              </div>
              <StoryPromptForm
                onSubmit={handleGenerate}
                loading={generating}
              />
            </motion.div>

            {/* Current Job Status */}
            {currentJob && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="card p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-dark-900">Current Edit Job</h3>
                  <Badge
                    className={
                      currentJob.status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : currentJob.status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : currentJob.status === 'processing'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-700'
                    }
                  >
                    {currentJob.status}
                  </Badge>
                </div>

                {currentJob.status === 'queued' || currentJob.status === 'processing' ? (
                  <div className="flex items-center gap-3 text-dark-600">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Generating edit plan with AI...</span>
                  </div>
                ) : currentJob.status === 'completed' && currentJob.llm_plan ? (
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                        <span className="font-semibold text-green-900">Edit Plan Generated!</span>
                      </div>
                      <p className="text-sm text-green-700">
                        {currentJob.llm_plan.edl?.length || 0} segments •{' '}
                        {currentJob.llm_plan.key_moments?.length || 0} key moments
                      </p>
                    </div>

                    {/* Aspect Ratio Selection */}
                    <div>
                      <label className="text-sm font-medium text-dark-700 mb-2 block">
                        Export Formats
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {ASPECT_RATIOS.map((ratio) => (
                          <button
                            key={ratio.value}
                            onClick={() => {
                              const current = selectedAspectRatios;
                              const newRatios = current.includes(ratio.value)
                                ? current.filter((r) => r !== ratio.value)
                                : [...current, ratio.value];
                              setSelectedAspectRatios(newRatios);
                            }}
                            className={`px-4 py-2 rounded-lg border transition-all ${
                              selectedAspectRatios.includes(ratio.value)
                                ? 'bg-primary-500/20 border-primary-500 text-primary-700'
                                : 'bg-white border-dark-200 text-dark-700 hover:border-primary-300'
                            }`}
                          >
                            <span className="mr-2">{ratio.icon}</span>
                            {ratio.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Apply Button */}
                    <Button
                      variant="primary"
                      icon={Film}
                      onClick={handleApply}
                      disabled={applying || selectedAspectRatios.length === 0}
                      className="w-full"
                    >
                      {applying ? 'Applying Edit...' : 'Apply Edit & Render Video'}
                    </Button>
                  </div>
                ) : currentJob.status === 'failed' ? (
                  <div className="p-4 rounded-lg bg-red-50 border border-red-200">
                    <div className="flex items-center gap-2 mb-2">
                      <XCircle className="w-5 h-5 text-red-600" />
                      <span className="font-semibold text-red-900">Generation Failed</span>
                    </div>
                    <p className="text-sm text-red-700">
                      {currentJob.error_message || 'Unknown error occurred'}
                    </p>
                  </div>
                ) : null}
              </motion.div>
            )}

            {/* Edit Plan Viewer */}
            {currentJob?.status === 'completed' && currentJob?.llm_plan && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <EditPlanViewer
                  plan={currentJob.llm_plan}
                  videoDuration={data.video_duration}
                />
              </motion.div>
            )}

            {/* Story Arc Timeline */}
            {currentJob?.status === 'completed' &&
              currentJob?.llm_plan?.story_analysis &&
              data.video_duration && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <StoryArcTimeline
                    storyAnalysis={currentJob.llm_plan.story_analysis}
                    videoDuration={data.video_duration}
                    keyMoments={currentJob.llm_plan.key_moments || []}
                  />
                </motion.div>
              )}

            {/* Video Comparison: Original vs Edited */}
            {(originalVideoUrl || editJobStatus) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="card p-6"
              >
                <div className="flex items-center gap-2 mb-6">
                  <Video size={20} className="text-primary-600" />
                  <h2 className="text-xl font-semibold text-dark-900">Video Comparison</h2>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {/* Original Video */}
                  <div>
                    <h3 className="text-sm font-medium text-dark-700 mb-3">Original Video</h3>
                    {originalVideoUrl ? (
                      <VideoPlayer src={originalVideoUrl} className="w-full aspect-video" />
                    ) : (
                      <div className="w-full aspect-video bg-dark-100 rounded-lg flex items-center justify-center">
                        <p className="text-dark-500">Video not found</p>
                      </div>
                    )}
                  </div>

                  {/* Edited Video */}
                  <div>
                    <h3 className="text-sm font-medium text-dark-700 mb-3">AI Edited Video</h3>
                    {editJobStatus?.status === 'completed' && editJobStatus?.output_paths ? (
                      <div className="space-y-3">
                        {Object.entries(editJobStatus.output_paths).map(([aspectRatio, path]) => {
                          // Convert path to URL
                          const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                          let videoUrl;
                          if (path.startsWith('http://') || path.startsWith('https://')) {
                            videoUrl = path;
                          } else if (path.startsWith('/storage/')) {
                            // Already a proper URL path from backend
                            videoUrl = `${apiBase}${path}`;
                          } else if (path.startsWith('../storage/')) {
                            // Relative path with .. - remove the ../
                            videoUrl = `${apiBase}${path.replace('../', '/')}`;
                          } else {
                            // Relative path - construct URL
                            videoUrl = `${apiBase}${path.startsWith('/') ? path : `/${path}`}`;
                          }
                          
                          return (
                            <div key={aspectRatio} className="space-y-2">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-dark-700">
                                  {aspectRatio} Format
                                </span>
                                <a
                                  href={videoUrl}
                                  download
                                  className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1 px-2 py-1 rounded hover:bg-primary-50"
                                >
                                  <Download size={14} />
                                  Download
                                </a>
                              </div>
                              <VideoPlayer src={videoUrl} className="w-full aspect-video rounded-lg border border-dark-200" />
                            </div>
                          );
                        })}
                      </div>
                    ) : editJobStatus?.status === 'processing' || editJobStatus?.status === 'queued' ? (
                      <div className="w-full aspect-video bg-dark-100 rounded-lg flex flex-col items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-600 mb-2" />
                        <p className="text-dark-600 text-sm">Rendering video...</p>
                      </div>
                    ) : editJobStatus?.status === 'failed' ? (
                      <div className="w-full aspect-video bg-red-50 rounded-lg flex items-center justify-center border border-red-200">
                        <div className="text-center">
                          <XCircle className="w-8 h-8 text-red-600 mx-auto mb-2" />
                          <p className="text-red-700 text-sm">
                            {editJobStatus.error_message || 'Rendering failed'}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full aspect-video bg-dark-100 rounded-lg flex items-center justify-center">
                        <p className="text-dark-500 text-sm">Click "Apply Edit" to render video</p>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Right Column - Data & History */}
          <div className="space-y-6">
            {/* Data Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-6"
            >
              <h3 className="text-lg font-semibold text-dark-900 mb-4">Data Available</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-600">Frames</span>
                  <Badge
                    className={
                      data.frames?.has_data
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }
                  >
                    {data.frames?.count || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-600">Scenes</span>
                  <Badge
                    className={
                      data.scenes?.has_data
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }
                  >
                    {data.scenes?.count || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-600">Transcript</span>
                  <Badge
                    className={
                      data.transcription?.has_data
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }
                  >
                    {data.transcription?.segment_count || 0} segments
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-600">Duration</span>
                  <span className="text-sm font-semibold text-dark-900">
                    {formatDuration(data.video_duration || 0)}
                  </span>
                </div>
              </div>
            </motion.div>

            {/* Edit History */}
            {editJobs.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="card p-6"
              >
                <h3 className="text-lg font-semibold text-dark-900 mb-4">Edit History</h3>
                <div className="space-y-3">
                  <AnimatePresence>
                    {editJobs.map((job) => (
                      <motion.div
                        key={job.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="p-3 rounded-lg border border-dark-200 hover:border-primary-300 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono text-dark-500">
                            {job.id.substring(0, 8)}...
                          </span>
                          <Badge
                            className={
                              job.status === 'completed'
                                ? 'bg-green-100 text-green-700'
                                : job.status === 'failed'
                                ? 'bg-red-100 text-red-700'
                                : job.status === 'processing'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-gray-100 text-gray-700'
                            }
                          >
                            {job.status}
                          </Badge>
                        </div>
                        {job.has_plan && (
                          <button
                            onClick={() => {
                              setCurrentJob({ job_id: job.id, status: job.status });
                              loadJobStatus(job.id);
                            }}
                            className="text-xs text-primary-600 hover:text-primary-700"
                          >
                            View Plan →
                          </button>
                        )}
                        {job.has_output && (
                          <div className="mt-2 pt-2 border-t border-dark-200">
                            <p className="text-xs text-dark-600 mb-1">Downloads:</p>
                            <div className="flex flex-wrap gap-1">
                              {['16:9', '9:16', '1:1'].map((ratio) => (
                                <button
                                  key={ratio}
                                  onClick={() => handleDownload(job.id, ratio)}
                                  className="text-xs px-2 py-1 bg-dark-100 hover:bg-dark-200 rounded text-dark-700"
                                >
                                  {ratio}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

