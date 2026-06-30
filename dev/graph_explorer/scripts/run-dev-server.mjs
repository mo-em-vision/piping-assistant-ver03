import { spawn } from 'node:child_process'
import { appendFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../../..')
const logPath = resolve(repoRoot, 'debug-b5dce6.log')

function debugLog(hypothesisId, message, data) {
  const line = JSON.stringify({
    sessionId: 'b5dce6',
    hypothesisId,
    location: 'run-dev-server.mjs',
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

debugLog('B', 'spawning python dev server', {
  repoRoot,
  cwd: process.cwd(),
  python: process.env.PYTHON ?? 'python',
})

const child = spawn(process.env.PYTHON ?? 'python', ['-m', 'dev.graph_explorer'], {
  cwd: repoRoot,
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    PROJECT_ROOT: repoRoot,
    PYTHONPATH: repoRoot,
  },
})

child.on('error', (error) => {
  debugLog('B', 'python spawn error', { error: String(error) })
  process.exit(1)
})

child.on('exit', (code, signal) => {
  debugLog('B', 'python process exited', { code, signal })
  process.exit(code ?? 1)
})
