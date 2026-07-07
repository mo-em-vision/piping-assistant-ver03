import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

import { repoRoot, resolveAliases } from './resolveAliases.mjs'

const desktopAppDir = __dirname

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      ...Object.entries(resolveAliases).map(([find, replacement]) => ({ find, replacement })),
      {
        find: /^zustand$/,
        replacement: path.join(desktopAppDir, 'node_modules/zustand/esm/index.mjs'),
      },
    ],
  },
  optimizeDeps: {
    exclude: ['zustand'],
  },
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup/vitest.setup.ts'],
    include: [
      'tests/**/*.{test,spec}.{ts,tsx}',
      `${repoRoot.replace(/\\/g, '/')}/dev/desktop_ui/tests/**/*.{test,spec}.{ts,tsx}`,
    ],
    exclude: ['tests/e2e/**'],
    env: {
      VITE_MOCK_DATA: 'false',
      VITE_BACKEND_URL: 'http://localhost:8000',
    },
  },
})
