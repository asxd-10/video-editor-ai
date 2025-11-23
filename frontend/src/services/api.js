import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`${response.config.method.toUpperCase()} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`${error.config?.method?.toUpperCase()} ${error.config?.url}`, error.response?.data);
    return Promise.reject(error);
  }
);

// Video API endpoints
export const videoAPI = {
  // Upload video
  upload: async (file, metadata = {}, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.description) formData.append('description', metadata.description);

    return api.post('/api/videos/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress?.(percentCompleted);
      },
    });
  },

  // Chunked upload
  uploadChunk: async (videoId, chunkNumber, totalChunks, filename, chunkBlob, onProgress) => {
    const formData = new FormData();
    formData.append('video_id', videoId);
    formData.append('chunk_number', chunkNumber);
    formData.append('total_chunks', totalChunks);
    formData.append('filename', filename);
    formData.append('file', chunkBlob);

    return api.post('/api/videos/chunk', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress?.(percentCompleted, chunkNumber);
      },
    });
  },

  // Get video details
  getVideo: (videoId) => api.get(`/api/videos/${videoId}`),

  // List videos
  listVideos: (params = {}) => api.get('/api/videos/', { params }),

  // Get processing logs
  getLogs: (videoId) => api.get(`/api/videos/${videoId}/logs`),

  // Delete video
  deleteVideo: (videoId) => api.delete(`/api/videos/${videoId}`),

  // Transcription
  startTranscription: (videoId) => api.post(`/api/videos/${videoId}/transcribe`),
  getTranscript: (videoId) => api.get(`/api/videos/${videoId}/transcript`),
  getTranscriptStatus: (videoId) => api.get(`/api/videos/${videoId}/transcript/status`),

  // Analysis
  startAnalysis: (videoId) => api.post(`/api/videos/${videoId}/analyze`),

  // Clip Candidates
  getCandidates: (videoId) => api.get(`/api/videos/${videoId}/candidates`),
  generateCandidates: (videoId) => api.post(`/api/videos/${videoId}/candidates`),

  // Edit Jobs
  createEditJob: (videoId, data) => api.post(`/api/videos/${videoId}/edit`, data),
  getEditJob: (videoId, jobId) => api.get(`/api/videos/${videoId}/edit/${jobId}`),
  listEditJobs: (videoId) => api.get(`/api/videos/${videoId}/edit`),
  downloadEditedVideo: (videoId, jobId, aspectRatio = '16:9') => 
    api.get(`/api/videos/${videoId}/edit/${jobId}/download`, {
      params: { aspect_ratio: aspectRatio },
      responseType: 'blob'
    }),

  // AI Edit Jobs
  getAIEditData: (videoId) => api.get(`/api/videos/${videoId}/ai-edit/data`),
  generateAIEdit: (videoId, data) => api.post(`/api/videos/${videoId}/ai-edit/generate`, data),
  getAIEditPlan: (videoId, jobId) => api.get(`/api/videos/${videoId}/ai-edit/plan/${jobId}`),
  applyAIEdit: (videoId, jobId, aspectRatios = ['16:9']) => 
    api.post(`/api/videos/${videoId}/ai-edit/apply/${jobId}`, { aspect_ratios: aspectRatios }),
  listAIEditJobs: (videoId) => api.get(`/api/videos/${videoId}/ai-edit`),
};

export default api;