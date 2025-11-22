import { create } from 'zustand';
import { videoAPI } from '../services/api';

export const useVideoStore = create((set, get) => ({
  videos: [],
  loading: false,
  error: null,
  selectedVideo: null,
  
  fetchVideos: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await videoAPI.listVideos(params);
      set({ videos: response.data.videos, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  fetchVideo: async (videoId) => {
    set({ loading: true, error: null });
    try {
      const response = await videoAPI.getVideo(videoId);
      set({ selectedVideo: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  addVideo: (video) => {
    set((state) => ({
      videos: [video, ...state.videos],
    }));
  },
  
  updateVideo: (videoId, updates) => {
    set((state) => ({
      videos: state.videos.map((v) => (v.id === videoId ? { ...v, ...updates } : v)),
      selectedVideo: state.selectedVideo?.id === videoId 
        ? { ...state.selectedVideo, ...updates } 
        : state.selectedVideo,
    }));
  },
}));