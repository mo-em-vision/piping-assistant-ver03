import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../../..')

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

child.on('error', () => {
  process.exit(1)
})

child.on('exit', (code) => {
  process.exit(code ?? 1)
})
