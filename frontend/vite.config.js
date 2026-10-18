import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // onnxruntime-web loads its own .wasm files; let Vite serve them as they are.
  optimizeDeps: { exclude: ['onnxruntime-web'] },
  worker: { format: 'es' }, // the cut-out worker is an ES module
  server: {
    // Send /api requests to the FastAPI backend, so the app and API share one address.
    // Set ADAA_API_URL to use a backend on another port.
    proxy: { '/api': process.env.ADAA_API_URL || 'http://127.0.0.1:8000' },
  },
});
