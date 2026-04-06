// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // CRÍTICO: Forzar una única versión de React para evitar duplicados
      'react': path.resolve('./node_modules/react'),
      'react-dom': path.resolve('./node_modules/react-dom'),
      'react/jsx-runtime': path.resolve('./node_modules/react/jsx-runtime'),
      'react/jsx-dev-runtime': path.resolve('./node_modules/react/jsx-dev-runtime')
    },
    dedupe: ['react', 'react-dom']
  },
  server: {
    port: 3000,
    strictPort: true,
    host: '0.0.0.0',
    allowedHosts: ['localhost', '.ngrok-free.dev', '.ngrok.io'],
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 3000,
      path: '/vite-hmr'
    },
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        },
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      '/metrics': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        // ⭐ Nombres con hash para cache busting
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  },
  preview: {
    port: 3000
  }
})
