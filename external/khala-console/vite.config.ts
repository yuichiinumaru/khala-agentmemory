/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // Ensure graph libraries are pre-bundled efficiently
    include: ['graphology', 'sigma', 'graphology-layout-forceatlas2', 'lucide-react']
  },
  server: {
    host: true,
    port: 5173
  },
  build: {
    target: 'esnext',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor chunks for better caching
          'graph-core': ['graphology', 'sigma'],
          'react-vendor': ['react', 'react-dom'],
          'ui-icons': ['lucide-react']
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
});
