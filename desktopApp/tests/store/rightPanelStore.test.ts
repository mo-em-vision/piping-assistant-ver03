import { beforeEach, describe, expect, it } from 'vitest'

import { useRightPanelStore } from '@/store/rightPanelStore'

describe('rightPanelStore', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(false)
  })

  it('starts with Chat and Standards tabs when reset without a task', () => {
    const state = useRightPanelStore.getState()
    expect(state.tabs.map((tab) => tab.id)).toEqual(['chat', 'standards'])
    expect(state.activeTabId).toBe('chat')
  })

  it('reset(true) restores Task, Chat, and Standards pinned tabs', () => {
    useRightPanelStore.getState().reset(true)

    const state = useRightPanelStore.getState()
    expect(state.tabs.map((tab) => tab.id)).toEqual(['task', 'chat', 'standards'])
    expect(state.activeTabId).toBe('task')
  })

  it('syncForActiveTask(true) prepends Task tab', () => {
    useRightPanelStore.getState().syncForActiveTask(true)

    const state = useRightPanelStore.getState()
    expect(state.tabs.map((tab) => tab.id)).toEqual(['task', 'chat', 'standards'])
    expect(state.activeTabId).toBe('chat')
  })

  it('syncForActiveTask(false) removes Task tab and moves active tab to Chat', () => {
    useRightPanelStore.getState().reset(true)
    useRightPanelStore.getState().setActiveTab('task')

    useRightPanelStore.getState().syncForActiveTask(false)

    const state = useRightPanelStore.getState()
    expect(state.tabs.map((tab) => tab.id)).toEqual(['chat', 'standards'])
    expect(state.activeTabId).toBe('chat')
  })

  it('preserves dynamic tabs when syncing for active task', () => {
    useRightPanelStore.getState().openReferenceTab('B313-304.1.1', '§304.1.1')

    useRightPanelStore.getState().syncForActiveTask(true)

    const state = useRightPanelStore.getState()
    expect(state.tabs.map((tab) => tab.kind)).toEqual(['task', 'chat', 'standards', 'reference'])
  })

  it('does not close the Standards pinned tab', () => {
    useRightPanelStore.getState().closeTab('standards')

    expect(useRightPanelStore.getState().tabs.map((tab) => tab.id)).toEqual(['chat', 'standards'])
  })
})
