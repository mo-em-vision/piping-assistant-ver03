import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { resolvePythonExecutable } from '../../electron/services/pythonRuntime'

describe('resolvePythonExecutable', () => {
  it('prefers packaged venv python on Windows', () => {
    const repoRoot = mkdtempSync(join(tmpdir(), 'backend-pack-'))
    const pythonPath = join(repoRoot, '.venv', 'Scripts', 'python.exe')
    mkdirSync(join(repoRoot, '.venv', 'Scripts'), { recursive: true })
    writeFileSync(pythonPath, '')

    expect(resolvePythonExecutable(repoRoot)).toBe(pythonPath)
  })
})
