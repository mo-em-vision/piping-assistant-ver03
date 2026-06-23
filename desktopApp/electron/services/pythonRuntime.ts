import { existsSync } from 'node:fs'
import path from 'node:path'

export function resolvePythonExecutable(repoRoot: string): string {
  const packagedVenvWindows = path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
  if (existsSync(packagedVenvWindows)) {
    return packagedVenvWindows
  }

  const packagedVenvUnix = path.join(repoRoot, '.venv', 'bin', 'python')
  if (existsSync(packagedVenvUnix)) {
    return packagedVenvUnix
  }

  const embeddableWindows = path.join(repoRoot, 'python', 'python.exe')
  if (existsSync(embeddableWindows)) {
    return embeddableWindows
  }

  const devVenvWindows = path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
  if (existsSync(devVenvWindows)) {
    return devVenvWindows
  }

  const devVenvUnix = path.join(repoRoot, '.venv', 'bin', 'python')
  if (existsSync(devVenvUnix)) {
    return devVenvUnix
  }

  return process.platform === 'win32' ? 'python' : 'python3'
}
