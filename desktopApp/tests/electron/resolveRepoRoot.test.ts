import path from 'node:path'
import { describe, expect, it } from 'vitest'

import { resolveRepoRootFrom } from '../../electron/services/repoRoot'

describe('resolveRepoRootFrom', () => {
  it('finds the repo root from the desktop app directory', () => {
    const desktopAppDir = path.resolve(__dirname, '../..')
    const repoRoot = path.resolve(desktopAppDir, '..')

    expect(resolveRepoRootFrom(desktopAppDir)).toBe(repoRoot)
  })

  it('finds the repo root from dist-electron', () => {
    const desktopAppDir = path.resolve(__dirname, '../..')
    const distElectron = path.join(desktopAppDir, 'dist-electron')
    const repoRoot = path.resolve(desktopAppDir, '..')

    expect(resolveRepoRootFrom(distElectron)).toBe(repoRoot)
  })
})
