import { create } from 'zustand'

export type StandardsReferenceKind = 'node' | 'table'

export interface TableViewerContext {
  searchQuery?: string
  columnFilters?: Record<string, string>
  highlightKeys?: Record<string, string>
}

export type RightPanelTab =
  | { id: 'task'; kind: 'task'; title: 'Task' }
  | { id: 'chat'; kind: 'chat'; title: 'Chat' }
  | {
      id: string
      kind: 'reference'
      title: string
      referenceKind: StandardsReferenceKind
      referenceId: string
      viewerContext?: TableViewerContext
    }

const PINNED_TABS: RightPanelTab[] = [
  { id: 'task', kind: 'task', title: 'Task' },
  { id: 'chat', kind: 'chat', title: 'Chat' },
]

export interface OpenReferenceTabOptions {
  /** When false, add or update the tab without leaving the current panel view. */
  activate?: boolean
}

interface RightPanelState {
  tabs: RightPanelTab[]
  activeTabId: string
  openReferenceTab: (
    referenceId: string,
    title: string,
    referenceKind?: StandardsReferenceKind,
    viewerContext?: TableViewerContext,
    options?: OpenReferenceTabOptions,
  ) => void
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

  openReferenceTab: (referenceId, title, referenceKind = 'node', viewerContext, options) => {
    const activate = options?.activate ?? true
    const existing = get().tabs.find(
      (tab) =>
        tab.kind === 'reference' &&
        tab.referenceKind === referenceKind &&
        tab.referenceId === referenceId,
    )
    if (existing) {
      set((state) => ({
        activeTabId: activate ? existing.id : state.activeTabId,
        tabs: state.tabs.map((tab) =>
          tab.id === existing.id && tab.kind === 'reference'
            ? {
                ...tab,
                title,
                viewerContext: viewerContext ?? tab.viewerContext,
              }
            : tab,
        ),
      }))
      return
    }

    const id = referenceTabId(referenceKind, referenceId)
    set((state) => ({
      tabs: [
        ...state.tabs,
        {
          id,
          kind: 'reference',
          title,
          referenceKind,
          referenceId,
          viewerContext,
        },
      ],
      activeTabId: activate ? id : state.activeTabId,
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
