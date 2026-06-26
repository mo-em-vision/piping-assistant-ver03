import { create } from 'zustand'

export type StandardsReferenceKind = 'node' | 'table'

export interface TableViewerContext {
  searchQuery?: string
  columnFilters?: Record<string, string>
  highlightKeys?: Record<string, string>
}

export interface NodeViewerContext {
  subsectionId?: string
}

export type ReferenceViewerContext = TableViewerContext | NodeViewerContext

export type RightPanelTab =
  | { id: 'task'; kind: 'task'; title: 'Task' }
  | { id: 'chat'; kind: 'chat'; title: 'Chat' }
  | {
      id: string
      kind: 'reference'
      title: string
      referenceKind: StandardsReferenceKind
      referenceId: string
      viewerContext?: ReferenceViewerContext
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
    viewerContext?: ReferenceViewerContext,
    options?: OpenReferenceTabOptions,
  ) => void
  closeTab: (id: string) => void
  setActiveTab: (id: string) => void
  reset: () => void
}

function referenceTabId(
  referenceKind: StandardsReferenceKind,
  referenceId: string,
  subsectionId?: string,
): string {
  if (referenceKind === 'table') {
    return `ref-table-${referenceId}`
  }
  if (subsectionId) {
    return `ref-${referenceId}-${subsectionId}`
  }
  return `ref-${referenceId}`
}

function referenceTabsMatch(
  tab: RightPanelTab,
  referenceKind: StandardsReferenceKind,
  referenceId: string,
  subsectionId?: string,
): boolean {
  if (tab.kind !== 'reference') {
    return false
  }
  if (tab.referenceKind !== referenceKind || tab.referenceId !== referenceId) {
    return false
  }
  if (referenceKind === 'node') {
    const tabSubsectionId =
      tab.viewerContext && 'subsectionId' in tab.viewerContext
        ? tab.viewerContext.subsectionId
        : undefined
    return tabSubsectionId === subsectionId
  }
  return true
}

function nextActiveTabIdAfterClose(
  tabs: RightPanelTab[],
  closingId: string,
  currentActiveId: string,
): string {
  if (currentActiveId !== closingId) {
    return currentActiveId
  }

  const closingIndex = tabs.findIndex((tab) => tab.id === closingId)
  if (closingIndex < 0) {
    return currentActiveId
  }

  const leftTab = closingIndex > 0 ? tabs[closingIndex - 1] : undefined
  const rightTab = closingIndex < tabs.length - 1 ? tabs[closingIndex + 1] : undefined
  return leftTab?.id ?? rightTab?.id ?? 'task'
}

export const useRightPanelStore = create<RightPanelState>((set, get) => ({
  tabs: PINNED_TABS,
  activeTabId: 'task',

  openReferenceTab: (referenceId, title, referenceKind = 'node', viewerContext, options) => {
    const activate = options?.activate ?? true
    const subsectionId =
      referenceKind === 'node' && viewerContext && 'subsectionId' in viewerContext
        ? viewerContext.subsectionId
        : undefined
    const existing = get().tabs.find((tab) =>
      referenceTabsMatch(tab, referenceKind, referenceId, subsectionId),
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

    const id = referenceTabId(referenceKind, referenceId, subsectionId)
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
      const activeTabId = nextActiveTabIdAfterClose(state.tabs, id, state.activeTabId)
      return { tabs, activeTabId }
    })
  },

  setActiveTab: (id) => set({ activeTabId: id }),

  reset: () => set({ tabs: PINNED_TABS, activeTabId: 'task' }),
}))
