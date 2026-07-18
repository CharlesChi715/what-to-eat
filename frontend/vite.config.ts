import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd())
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'

  if (command === 'serve') {
    console.info(`[vite] proxy /api -> ${apiTarget}`)
  }

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': apiTarget,
      },
    },
  }
})
