import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useDevToolsStore } from '@/store/devToolsStore'
import { useRightPanelStore } from '@/store/rightPanelStore'

describe('rightPanelStore openNodeEditTab', () => {
  beforeEach(() => {
    useDevToolsStore.setState({ devModeActive: true })
    useRightPanelStore.getState().reset(true)
  })

  it('adds and activates a node-edit tab when dev mode is on', () => {
    useRightPanelStore.getState().openNodeEditTab('B313-304.1.2', {
      pack: 'asme_b31.3',
      sourceField: 'question',
      title: 'Material',
    })

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('edit-node-B313-304.1.2')
    const tab = state.tabs.find((item) => item.kind === 'node-edit')
    expect(tab).toMatchObject({
      nodeId: 'B313-304.1.2',
      pack: 'asme_b31.3',
      sourceField: 'question',
    })
  })

  it('reuses an existing node-edit tab for the same node', () => {
    const { openNodeEditTab } = useRightPanelStore.getState()
    openNodeEditTab('B313-304.1.2')
    openNodeEditTab('B313-304.1.2', { sourceField: 'title' })

    const state = useRightPanelStore.getState()
    const editTabs = state.tabs.filter((tab) => tab.kind === 'node-edit')
    expect(editTabs).toHaveLength(1)
    expect(editTabs[0]?.sourceField).toBe('title')
  })

  it('does not open node-edit tab when dev mode is off', () => {
    useDevToolsStore.setState({ devModeActive: false })

    useRightPanelStore.getState().openNodeEditTab('B313-304.1.2')

    const state = useRightPanelStore.getState()
    expect(state.tabs.some((tab) => tab.kind === 'node-edit')).toBe(false)
  })
})
