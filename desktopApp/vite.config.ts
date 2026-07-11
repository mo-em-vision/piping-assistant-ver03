import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import electron from 'vite-plugin-electron/simple'

import { repoRoot, resolveAliases } from './resolveAliases.mjs'

const desktopAppDir = __dirname

export default defineConfig({
  plugins: [
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
    fs: {
      allow: [repoRoot],
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
    },
  },
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
})
