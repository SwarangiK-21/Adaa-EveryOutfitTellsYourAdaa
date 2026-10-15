import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // Send /api requests to the FastAPI backend, so the app and API share one address.
    // Set ADAA_API_URL to use a backend on another port.
    proxy: { '/api': process.env.ADAA_API_URL || 'http://127.0.0.1:8000' },
  },
});
