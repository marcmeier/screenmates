import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev server proxies the API to the FastAPI backend on :8000 so the SPA
// runs same-origin (cookies work) during development.
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },

    },
  },
})
