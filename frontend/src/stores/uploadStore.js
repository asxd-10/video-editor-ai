import { create } from 'zustand';

export const useUploadStore = create((set, get) => ({
  uploads: [],
  
  addUpload: (upload) => {
    set((state) => ({
      uploads: [...state.uploads, upload],
    }));
  },
  
  updateUpload: (id, updates) => {
    set((state) => ({
      uploads: state.uploads.map((upload) =>
        upload.id === id ? { ...upload, ...updates } : upload
      ),
    }));
  },
  
  removeUpload: (id) => {
    set((state) => ({
      uploads: state.uploads.filter((upload) => upload.id !== id),
    }));
  },
  
  clearCompleted: () => {
    set((state) => ({
      uploads: state.uploads.filter((upload) => upload.status !== 'completed'),
    }));
  },
}));