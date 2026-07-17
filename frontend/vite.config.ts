import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Where /api/* calls are forwarded during development.
// Default: backend on this machine. To use the PC backend instead:
//   VITE_API_TARGET=http://192.168.0.12:8000 npm run dev
const apiTarget = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': apiTarget,
    },
  },
})
