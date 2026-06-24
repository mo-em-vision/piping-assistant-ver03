import { create } from 'zustand'

export type StandardsReferenceKind = 'node' | 'table'

export type RightPanelTab =
  | { id: 'task'; kind: 'task'; title: 'Task' }
  | { id: 'chat'; kind: 'chat'; title: 'Chat' }
  | {
      id: string
      kind: 'reference'
      title: string
      referenceKind: StandardsReferenceKind
      referenceId: string
    }

const PINNED_TABS: RightPanelTab[] = [
  { id: 'task', kind: 'task', title: 'Task' },
  { id: 'chat', kind: 'chat', title: 'Chat' },
]

interface RightPanelState {
  tabs: RightPanelTab[]
  activeTabId: string
  openReferenceTab: (referenceId: string, title: string, referenceKind?: StandardsReferenceKind) => void
  closeTab: (id: string) => void
  setActiveTab: (id: string) => void
  reset: () => void
}

function referenceTabId(referenceKind: StandardsReferenceKind, referenceId: string): string {
  return referenceKind === 'table' ? `ref-table-${referenceId}` : `ref-${referenceId}`
}

export const useRightPanelStore = create<RightPanelState>((set, get) => ({
  tabs: PINNED_TABS,
  activeTabId: 'task',

  openReferenceTab: (referenceId, title, referenceKind = 'node') => {
    const existing = get().tabs.find(
      (tab) =>
        tab.kind === 'reference' &&
        tab.referenceKind === referenceKind &&
        tab.referenceId === referenceId,
    )
    if (existing) {
      set({ activeTabId: existing.id })
      return
    }

    const id = referenceTabId(referenceKind, referenceId)
    set((state) => ({
      tabs: [...state.tabs, { id, kind: 'reference', title, referenceKind, referenceId }],
      activeTabId: id,
    }))
  },

  closeTab: (id) => {
    if (id === 'task' || id === 'chat') {
      return
    }

    set((state) => {
      const tabs = state.tabs.filter((tab) => tab.id !== id)
      const activeTabId = state.activeTabId === id ? 'task' : state.activeTabId
      return { tabs, activeTabId }
    })
  },

  setActiveTab: (id) => set({ activeTabId: id }),

  reset: () => set({ tabs: PINNED_TABS, activeTabId: 'task' }),
}))
