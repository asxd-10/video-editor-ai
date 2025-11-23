import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Download, 
  Loader2, 
  CheckCircle2, 
  XCircle,
  Film,
  Sparkles
} from 'lucide-react';
import { videoAPI } from '../../services/api';
import clsx from 'clsx';

const ASPECT_RATIOS = [
  { value: '16:9', label: 'YouTube (16:9)', icon: '📺' },
  { value: '9:16', label: 'TikTok/Reels (9:16)', icon: '📱' },
  { value: '1:1', label: 'Instagram (1:1)', icon: '📸' },
];

export default function EditJobManager({ videoId, clipCandidateId, onEditComplete, hasAnalysis, analysisMetadata, videoDuration }) {
  const [editJobs, setEditJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [hasTranscript, setHasTranscript] = useState(false);
  const [editOptions, setEditOptions] = useState({
    remove_silence: true,
    jump_cuts: true,
    dynamic_zoom: false,
    captions: true,
    caption_style: 'burn_in',
    pace_optimize: false,
    aspect_ratios: ['16:9'],
  });

  // Check if transcript exists (optional - editing works without it, but with limited features)
  // Only check once on mount and when videoId changes - don't poll continuously
  // The parent component (VideoView) handles polling for transcript status
  useEffect(() => {
    const checkTranscript = async () => {
      try {
        const response = await videoAPI.getTranscriptStatus(videoId);
        setHasTranscript(response.data.status === 'complete');
      } catch (error) {
        setHasTranscript(false);
      }
    };
    checkTranscript();
    // Only check once - parent component handles polling
  }, [videoId]);

  // Load edit jobs on mount
  useEffect(() => {
    loadEditJobs();
  }, [videoId]);

  // Poll for job updates
  useEffect(() => {
    const interval = setInterval(() => {
      const hasProcessing = editJobs.some(job => 
        job.status === 'queued' || job.status === 'processing'
      );
      if (hasProcessing) {
        loadEditJobs();
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [editJobs, videoId]);

  const loadEditJobs = async () => {
    try {
      const response = await videoAPI.listEditJobs(videoId);
      setEditJobs(response.data.jobs || []);
    } catch (error) {
      console.error('Failed to load edit jobs:', error);
    }
  };

  const handleCreateEdit = async () => {
    setCreating(true);
    try {
      const response = await videoAPI.createEditJob(videoId, {
        clip_candidate_id: clipCandidateId || null,
        edit_options: editOptions,
      });
      
      // Reload jobs
      await loadEditJobs();
      onEditComplete?.(response.data.job_id);
    } catch (error) {
      console.error('Failed to create edit job:', error);
      alert('Failed to create edit job. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = async (jobId, aspectRatio) => {
    try {
      const response = await videoAPI.downloadEditedVideo(videoId, jobId, aspectRatio);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `edited_${aspectRatio.replace(':', '_')}.mp4`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download:', error);
      alert('Failed to download video. Please try again.');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'failed':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'processing':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Create Edit Section */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="w-6 h-6 text-purple-500" />
          <h3 className="text-xl font-semibold text-dark-900">Create Edit</h3>
        </div>

        {/* Edit Options */}
        <div className="space-y-4 mb-6">
          <div className="text-sm font-medium text-dark-700 mb-3">Edit Options</div>
          <div className="grid grid-cols-2 gap-4">
            <label className={clsx("flex items-center gap-3 cursor-pointer p-2 rounded-lg transition-colors", !hasAnalysis ? "opacity-50 cursor-not-allowed" : "hover:bg-dark-50")}>
              <input
                type="checkbox"
                checked={editOptions.remove_silence}
                onChange={(e) =>
                  setEditOptions({ ...editOptions, remove_silence: e.target.checked })
                }
                disabled={!hasAnalysis}
                className="w-5 h-5 rounded border-2 border-dark-300 bg-white text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 cursor-pointer accent-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <span className="text-dark-900 font-medium">
                Remove Silence {!hasAnalysis && <span className="text-xs text-yellow-700">(needs analysis)</span>}
              </span>
            </label>

            <label className={clsx("flex items-center gap-3 cursor-pointer p-2 rounded-lg transition-colors", !hasTranscript ? "opacity-50 cursor-not-allowed" : "hover:bg-dark-50")}>
              <input
                type="checkbox"
                checked={editOptions.jump_cuts}
                onChange={(e) =>
                  setEditOptions({ ...editOptions, jump_cuts: e.target.checked })
                }
                disabled={!hasTranscript}
                className="w-5 h-5 rounded border-2 border-dark-300 bg-white text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 cursor-pointer accent-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <span className="text-dark-900 font-medium">
                Jump Cuts {!hasTranscript && <span className="text-xs text-yellow-600">(needs transcript)</span>}
              </span>
            </label>

            <label className={clsx("flex items-center gap-3 cursor-pointer p-2 rounded-lg transition-colors", !hasTranscript ? "opacity-50 cursor-not-allowed" : "hover:bg-dark-50")}>
              <input
                type="checkbox"
                checked={editOptions.captions}
                onChange={(e) =>
                  setEditOptions({ ...editOptions, captions: e.target.checked })
                }
                disabled={!hasTranscript}
                className="w-5 h-5 rounded border-2 border-dark-300 bg-white text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 cursor-pointer accent-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <span className="text-dark-900 font-medium">
                Auto Captions {!hasTranscript && <span className="text-xs text-yellow-600">(needs transcript)</span>}
              </span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-dark-50 transition-colors">
              <input
                type="checkbox"
                checked={editOptions.dynamic_zoom}
                onChange={(e) =>
                  setEditOptions({ ...editOptions, dynamic_zoom: e.target.checked })
                }
                className="w-5 h-5 rounded border-2 border-dark-300 bg-white text-purple-500 focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 cursor-pointer accent-purple-500"
              />
              <span className="text-dark-900 font-medium">Dynamic Zoom</span>
            </label>
          </div>

          {/* Aspect Ratios */}
          <div>
            <label className="block text-sm font-medium text-dark-700 mb-2">
              Export Formats
            </label>
            <div className="flex flex-wrap gap-2">
              {ASPECT_RATIOS.map((ratio) => (
                <button
                  key={ratio.value}
                  onClick={() => {
                    const current = editOptions.aspect_ratios;
                    const newRatios = current.includes(ratio.value)
                      ? current.filter((r) => r !== ratio.value)
                      : [...current, ratio.value];
                    setEditOptions({ ...editOptions, aspect_ratios: newRatios });
                  }}
                  className={clsx(
                    'px-4 py-2 rounded-lg border transition-all',
                    editOptions.aspect_ratios.includes(ratio.value)
                      ? 'bg-purple-100 border-purple-500 text-purple-700'
                      : 'bg-white border-dark-200 text-dark-700 hover:border-purple-300 hover:bg-purple-50'
                  )}
                >
                  <span className="mr-2">{ratio.icon}</span>
                  {ratio.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Info messages */}
        {!hasAnalysis && (
          <div className="mb-4 p-3 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm">
            ⚠️ Run analysis first to enable silence removal. Basic editing (aspect ratio conversion) works without analysis.
          </div>
        )}
        {!hasTranscript && (
          <div className="mb-4 p-3 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm">
            ⚠️ Transcribe the video first to enable advanced features (jump cuts, captions).
          </div>
        )}

        {/* Create Button - Allow editing even without transcript */}
        <button
          onClick={handleCreateEdit}
          disabled={creating || editOptions.aspect_ratios.length === 0}
          className={clsx(
            'w-full py-3 px-6 rounded-xl font-semibold transition-all flex items-center justify-center gap-2',
            creating || editOptions.aspect_ratios.length === 0
              ? 'bg-gray-500/20 text-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
          )}
        >
          {creating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Creating Edit...
            </>
          ) : (
            <>
              <Film className="w-5 h-5" />
              Create Auto-Edit
            </>
          )}
        </button>
      </div>

      {/* Edit Jobs List */}
      {editJobs.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-dark-900 mb-4">Edit History</h3>
          <div className="space-y-3">
            <AnimatePresence>
              {editJobs.map((job) => (
                <motion.div
                  key={job.job_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={clsx(
                    'p-4 rounded-xl border',
                    getStatusColor(job.status)
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <span className="font-medium capitalize">{job.status}</span>
                      {job.clip_candidate_id && (
                        <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-700">
                          From Clip
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-dark-500">
                      {new Date(job.created_at).toLocaleString()}
                    </span>
                  </div>

                  {job.status === 'completed' && job.output_paths && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-dark-900 mb-2">Download:</div>
                      <div className="flex flex-wrap gap-2">
                        {Object.keys(job.output_paths).map((aspectRatio) => {
                          const ratio = ASPECT_RATIOS.find((r) => r.value === aspectRatio);
                          return (
                            <button
                              key={aspectRatio}
                              onClick={() => handleDownload(job.job_id, aspectRatio)}
                              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-purple-100 hover:bg-purple-200 text-purple-700 transition-colors text-sm"
                            >
                              <Download className="w-4 h-4" />
                              {ratio ? ratio.label : aspectRatio}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {job.status === 'failed' && job.error_message && (
                    <div className="text-sm text-red-600 mt-2">
                      Error: {job.error_message}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}

