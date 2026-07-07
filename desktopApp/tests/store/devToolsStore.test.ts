import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useDevToolsStore } from '@/store/devToolsStore'

vi.mock('@/config/env', () => ({
  env: { devToolsAvailable: true },
}))

describe('devToolsStore', () => {
  beforeEach(() => {
    useDevToolsStore.setState({ devModeActive: false })
    vi.restoreAllMocks()
  })

  it('persists dev mode activation', () => {
    useDevToolsStore.getState().setDevModeActive(true)
    expect(useDevToolsStore.getState().devModeActive).toBe(true)
    expect(localStorage.getItem('devModeActive')).toBe('1')
  })

  it('toggles dev mode', () => {
    useDevToolsStore.getState().toggleDevMode()
    expect(useDevToolsStore.getState().devModeActive).toBe(true)
    useDevToolsStore.getState().toggleDevMode()
    expect(useDevToolsStore.getState().devModeActive).toBe(false)
  })
})
