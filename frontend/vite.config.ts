import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Override with SETUBIZ_API when the backend is not on the default port.
const apiTarget = process.env.SETUBIZ_API ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': apiTarget },
  },
})
