import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// While developing, any request that starts with /api is passed on to Django on port 8000.
// That way the browser only ever talks to one address and CORS is not a problem.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})