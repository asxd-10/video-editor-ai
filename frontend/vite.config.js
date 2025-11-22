// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // This tells Vite to redirect any requests starting with /api
    // (e.g., http://localhost:5173/api/videos) to your backend.
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // Adjust this port if your backend uses a different one
        changeOrigin: true,
        secure: false,
        // rewrite: (path) => path.replace(/^\/api/, ''), // Often needed if your backend doesn't expect /api
      },
    },
  },
});