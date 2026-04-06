import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  server: {
    port: 5174,
    proxy: {
      '/portal/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../../backend/static/portal',
    emptyOutDir: true,
  },
});
