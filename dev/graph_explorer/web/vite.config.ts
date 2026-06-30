import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { appendFileSync } from 'node:fs'
import { resolve } from 'node:path'

const repoRoot = resolve(__dirname, '../../..')
const logPath = resolve(repoRoot, 'debug-b5dce6.log')

function debugLog(hypothesisId: string, message: string, data: Record<string, unknown>) {
  const line = JSON.stringify({
    sessionId: 'b5dce6',
    hypothesisId,
    location: 'vite.config.ts',
    message,
    data,
    timestamp: Date.now(),
    runId: process.env.DEBUG_RUN_ID ?? 'pre-fix',
  })
  try {
    appendFileSync(logPath, `${line}\n`)
  } catch {
    // ignore
  }
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'graph-explorer-debug-logger',
      configureServer(server) {
        server.httpServer?.once('listening', () => {
          const address = server.httpServer?.address()
          debugLog('C', 'vite server listening', { address })
          debugLog('D', 'vite host binding', {
            configuredHost: true,
            note: 'listening on all interfaces (localhost and 127.0.0.1)',
          })
        })
        server.httpServer?.on('error', (error: NodeJS.ErrnoException) => {
          debugLog('E', 'vite server error', { code: error.code, message: error.message })
        })
      },
    },
  ],
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8765',
      '/ws': {
        target: 'ws://127.0.0.1:8765',
        ws: true,
      },
      '/health': 'http://127.0.0.1:8765',
    },
  },
})
