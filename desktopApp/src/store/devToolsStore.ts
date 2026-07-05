import { create } from 'zustand'

import { env } from '@/config/env'

const STORAGE_KEY = 'devModeActive'

function readPersisted(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function persist(active: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, active ? '1' : '0')
  } catch {
    // ignore
  }
}

async function closeNodeEditTabs(): Promise<void> {
  const { useRightPanelStore } = await import('@/store/rightPanelStore')
  const state = useRightPanelStore.getState()
  for (const tab of state.tabs) {
    if (tab.kind === 'node-edit') {
      state.closeTab(tab.id)
    }
  }
}

async function syncElectronDevMode(active: boolean): Promise<void> {
  const api = window.electronAPI
  if (!api?.syncDevMode) {
    return
  }
  await api.syncDevMode(active)
}

async function closeInspector(): Promise<void> {
  try {
    const module = await import('@dev-ui/inspector/inspectorStore')
    module.useInspectorStore.getState().setOpen(false)
  } catch {
    // dev-ui not loaded
  }
}

interface DevToolsState {
  devModeActive: boolean
  setDevModeActive: (active: boolean) => void
  toggleDevMode: () => void
}

export const useDevToolsStore = create<DevToolsState>((set, get) => ({
  devModeActive: env.devToolsAvailable ? readPersisted() : false,

  setDevModeActive: (active) => {
    if (!env.devToolsAvailable) {
      return
    }
    set({ devModeActive: active })
    persist(active)
    if (!active) {
      void closeInspector()
      void closeNodeEditTabs()
    }
    void syncElectronDevMode(active)
  },

  toggleDevMode: () => {
    get().setDevModeActive(!get().devModeActive)
  },
}))
