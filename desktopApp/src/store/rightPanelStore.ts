import { create } from 'zustand'

import { env } from '@/config/env'
import { useDevToolsStore } from '@/store/devToolsStore'

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
  | { id: 'standards'; kind: 'standards'; title: 'Standards' }
  | {
      id: string
      kind: 'reference'
      title: string
      referenceKind: StandardsReferenceKind
      referenceId: string
      viewerContext?: ReferenceViewerContext
    }
  | {
      id: string
      kind: 'material'
      title: string
      materialId: string
    }
  | {
      id: string
      kind: 'node-edit'
      title: string
      nodeId: string
      pack: string
      sourceField?: string | null
    }

const TASK_TAB: RightPanelTab = { id: 'task', kind: 'task', title: 'Task' }
const CHAT_TAB: RightPanelTab = { id: 'chat', kind: 'chat', title: 'Chat' }
const STANDARDS_TAB: RightPanelTab = { id: 'standards', kind: 'standards', title: 'Standards' }

function pinnedTabsForActiveTask(hasTask: boolean): RightPanelTab[] {
  const pinned = [CHAT_TAB, STANDARDS_TAB]
  return hasTask ? [TASK_TAB, ...pinned] : pinned
}

function defaultActiveTabId(hasTask: boolean): string {
  return hasTask ? 'task' : 'chat'
}

export interface OpenReferenceTabOptions {
  /** When false, add or update the tab without leaving the current panel view. */
  activate?: boolean
}

export type OpenMaterialTabOptions = OpenReferenceTabOptions

export interface OpenNodeEditTabOptions {
  pack?: string
  sourceField?: string | null
  title?: string
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
  openMaterialTab: (materialId: string, title: string, options?: OpenMaterialTabOptions) => void
  openNodeEditTab: (nodeId: string, options?: OpenNodeEditTabOptions) => void
  closeTab: (id: string) => void
  setActiveTab: (id: string) => void
  reset: (hasTask?: boolean) => void
  syncForActiveTask: (hasTask: boolean) => void
}

function materialTabId(materialId: string): string {
  return `material-${materialId}`
}

function nodeEditTabId(nodeId: string): string {
  return `edit-node-${nodeId}`
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
  const remainingTabs = tabs.filter((tab) => tab.id !== closingId)
  return leftTab?.id ?? rightTab?.id ?? remainingTabs[0]?.id ?? 'chat'
}

export const useRightPanelStore = create<RightPanelState>((set, get) => ({
  tabs: pinnedTabsForActiveTask(false),
  activeTabId: 'chat',

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

  openMaterialTab: (materialId, title, options) => {
    const activate = options?.activate ?? true
    const id = materialTabId(materialId)
    const existing = get().tabs.find((tab) => tab.kind === 'material' && tab.materialId === materialId)
    if (existing) {
      set((state) => ({
        activeTabId: activate ? existing.id : state.activeTabId,
        tabs: state.tabs.map((tab) =>
          tab.id === existing.id && tab.kind === 'material' ? { ...tab, title } : tab,
        ),
      }))
      return
    }

    set((state) => ({
      tabs: [
        ...state.tabs,
        {
          id,
          kind: 'material',
          title,
          materialId,
        },
      ],
      activeTabId: activate ? id : state.activeTabId,
    }))
  },

  openNodeEditTab: (nodeId, options) => {
    if (!env.devToolsAvailable || !useDevToolsStore.getState().devModeActive) {
      return
    }
    const pack = options?.pack ?? 'asme_b31.3'
    const activate = options?.activate ?? true
    const title = options?.title ? `Edit: ${options.title}` : `Edit: ${nodeId}`
    const id = nodeEditTabId(nodeId)
    const existing = get().tabs.find((tab) => tab.kind === 'node-edit' && tab.nodeId === nodeId)

    if (existing) {
      set((state) => ({
        activeTabId: activate ? existing.id : state.activeTabId,
        tabs: state.tabs.map((tab) =>
          tab.id === existing.id && tab.kind === 'node-edit'
            ? {
                ...tab,
                title,
                pack,
                sourceField: options?.sourceField ?? tab.sourceField ?? null,
              }
            : tab,
        ),
      }))
      return
    }

    set((state) => ({
      tabs: [
        ...state.tabs,
        {
          id,
          kind: 'node-edit',
          title,
          nodeId,
          pack,
          sourceField: options?.sourceField ?? null,
        },
      ],
      activeTabId: activate ? id : state.activeTabId,
    }))
  },

  closeTab: (id) => {
    if (id === 'task' || id === 'chat' || id === 'standards') {
      return
    }

    set((state) => {
      const tabs = state.tabs.filter((tab) => tab.id !== id)
      const activeTabId = nextActiveTabIdAfterClose(state.tabs, id, state.activeTabId)
      return { tabs, activeTabId }
    })
  },

  setActiveTab: (id) => set({ activeTabId: id }),

  reset: (hasTask = false) =>
    set({
      tabs: pinnedTabsForActiveTask(hasTask),
      activeTabId: defaultActiveTabId(hasTask),
    }),

  syncForActiveTask: (hasTask) => {
    set((state) => {
      const dynamicTabs = state.tabs.filter(
        (tab) => tab.kind === 'reference' || tab.kind === 'material' || tab.kind === 'node-edit',
      )
      const pinnedTabs = pinnedTabsForActiveTask(hasTask)
      const tabs = [...pinnedTabs, ...dynamicTabs]

      let activeTabId = state.activeTabId
      if (!tabs.some((tab) => tab.id === activeTabId)) {
        activeTabId = defaultActiveTabId(hasTask)
      } else if (!hasTask && activeTabId === 'task') {
        activeTabId = 'chat'
      }

      return { tabs, activeTabId }
    })
  },
}))
