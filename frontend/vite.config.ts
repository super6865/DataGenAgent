import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('antd')) {
              return 'antd';
            }
            if (id.includes('@ant-design/icons')) {
              return 'antd-icons';
            }
            if (id.includes('monaco-editor') || id.includes('@monaco-editor')) {
              return 'monaco-editor';
            }
            if (id.includes('xlsx')) {
              return 'xlsx';
            }
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})
