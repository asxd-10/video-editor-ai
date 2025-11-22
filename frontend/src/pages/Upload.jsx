import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, CheckCircle } from 'lucide-react';
import UploadZone from '../components/upload/UploadZone';
import UploadProgress from '../components/upload/UploadProgress';
import Button from '../components/common/Button';
import { videoAPI } from '../services/api';
import { useUploadStore } from '../stores/uploadStore';
import { useVideoStore } from '../stores/videoStore';

export default function Upload() {
  const navigate = useNavigate();
  const { uploads, addUpload, updateUpload } = useUploadStore();
  const { addVideo } = useVideoStore();
  
  const [selectedFile, setSelectedFile] = useState(null);
  const [metadata, setMetadata] = useState({ title: '', description: '' });
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setMetadata({ title: file.name, description: '' });
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    const uploadId = Date.now().toString();
    
    addUpload({
      id: uploadId,
      file: selectedFile,
      progress: 0,
      status: 'uploading',
    });

    setUploading(true);

    try {
      const response = await videoAPI.upload(
        selectedFile,
        metadata,
        (progress) => {
          updateUpload(uploadId, { progress });
        }
      );

      updateUpload(uploadId, { 
        status: 'processing', 
        progress: 100,
        videoId: response.data.video_id 
      });

      addVideo({
        id: response.data.video_id,
        title: metadata.title,
        filename: response.data.filename,
        status: response.data.status,
        file_size: response.data.file_size,
      });

      // Poll for completion
      pollVideoStatus(response.data.video_id, uploadId);

    } catch (error) {
      console.error('Upload failed:', error);
      updateUpload(uploadId, { 
        status: 'failed',
        error: error.response?.data?.detail || 'Upload failed'
      });
    } finally {
      setUploading(false);
    }
  };

  const pollVideoStatus = async (videoId, uploadId) => {
    const interval = setInterval(async () => {
      try {
        const response = await videoAPI.getVideo(videoId);
        const video = response.data;

        if (video.status === 'ready') {
          updateUpload(uploadId, { status: 'completed' });
          clearInterval(interval);
          
          // Navigate to video after 2 seconds
          setTimeout(() => {
            navigate(`/video/${videoId}`);
          }, 2000);
        } else if (video.status === 'failed') {
          updateUpload(uploadId, { 
            status: 'failed',
            error: video.error || 'Processing failed'
          });
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Polling failed:', error);
      }
    }, 2000);

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(interval), 5 * 60 * 1000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 py-12">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Button
            variant="ghost"
            icon={ArrowLeft}
            onClick={() => navigate('/')}
            className="mb-4"
          >
            Back
          </Button>
          <h1 className="text-4xl font-bold text-dark-900">Upload Video</h1>
          <p className="text-dark-600 mt-2">
            Upload your video and we'll handle the rest
          </p>
        </motion.div>

        {/* Upload Flow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {!selectedFile ? (
            <UploadZone onFileSelect={handleFileSelect} />
          ) : (
            <div className="space-y-6">
              {/* File Info & Metadata */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-dark-900 mb-4">
                  Video Details
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-700 mb-2">
                      Title
                    </label>
                    <input
                      type="text"
                      value={metadata.title}
                      onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
                      className="input"
                      placeholder="Enter video title"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-dark-700 mb-2">
                      Description (optional)
                    </label>
                    <textarea
                      value={metadata.description}
                      onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
                      className="input resize-none"
                      rows="3"
                      placeholder="Enter video description"
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <Button
                    variant="primary"
                    onClick={handleUpload}
                    loading={uploading}
                    disabled={!metadata.title.trim()}
                    className="flex-1"
                  >
                    Start Upload
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setSelectedFile(null)}
                    disabled={uploading}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {/* Upload Progress List */}
        <AnimatePresence>
          {uploads.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-8 space-y-4"
            >
              <h3 className="text-lg font-semibold text-dark-900">
                Upload Queue
              </h3>
              {uploads.map((upload) => (
                <UploadProgress key={upload.id} upload={upload} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}