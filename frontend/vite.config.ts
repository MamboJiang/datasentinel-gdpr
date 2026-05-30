import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        changeOrigin: true,
        target: process.env.DATASENTINEL_API_TARGET ?? 'http://127.0.0.1:8000',
      },
    },
  },
})
