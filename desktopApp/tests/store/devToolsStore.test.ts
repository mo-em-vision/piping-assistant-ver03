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

  it('syncs electron dev mode and closes inspector on deactivate', async () => {
    const syncDevMode = vi.fn().mockResolvedValue({ status: 'stopped', url: 'http://127.0.0.1:8765' })
    window.electronAPI = {
      platform: 'win32',
      getBackendStatus: vi.fn(),
      retryBackendConnection: vi.fn(),
      onBackendStatusChange: vi.fn(),
      getWindowDisplayState: vi.fn(),
      onWindowDisplayStateChange: vi.fn(),
      syncDevMode,
    }

    const inspectorModule = await import('@dev-ui/inspector/inspectorStore')
    inspectorModule.useInspectorStore.getState().setOpen(true)

    useDevToolsStore.getState().setDevModeActive(true)
    expect(syncDevMode).toHaveBeenCalledWith(true)

    useDevToolsStore.getState().setDevModeActive(false)
    expect(syncDevMode).toHaveBeenCalledWith(false)
    await vi.waitFor(() => {
      expect(inspectorModule.useInspectorStore.getState().open).toBe(false)
    })
  })
})
