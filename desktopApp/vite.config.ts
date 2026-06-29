import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import electron from 'vite-plugin-electron/simple'

const isStudioOnly = process.env.VITE_DEV_STUDIO === 'true'

export default defineConfig({
  plugins: isStudioOnly
    ? [react()]
    : [
        react(),
        electron({
          main: {
            entry: 'electron/main.ts',
          },
          preload: {
            input: path.join(__dirname, 'electron/preload.ts'),
          },
        }),
      ],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false,
  },
  build: {
    rollupOptions: {
      input: isStudioOnly
        ? { studio: path.resolve(__dirname, 'studio.html') }
        : { main: path.resolve(__dirname, 'index.html') },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
})
