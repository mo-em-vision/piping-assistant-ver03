import { existsSync } from 'node:fs'
import path from 'node:path'

const STANDARDS_MARKER = path.join('knowledge', 'standards')

/** Walk upward from `startDir` until the Ver03 repo root (`knowledge/standards`) is found. */
export function resolveRepoRootFrom(startDir: string): string {
  let dir = path.resolve(startDir)

  for (let depth = 0; depth < 8; depth += 1) {
    if (existsSync(path.join(dir, STANDARDS_MARKER))) {
      return dir
    }

    const parent = path.dirname(dir)
    if (parent === dir) {
      break
    }
    dir = parent
  }

  return path.resolve(startDir, '..')
}
