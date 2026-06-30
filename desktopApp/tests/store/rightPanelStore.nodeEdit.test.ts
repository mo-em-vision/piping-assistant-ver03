import { beforeEach, describe, expect, it } from 'vitest'

import { useRightPanelStore } from '@/store/rightPanelStore'

describe('rightPanelStore openNodeEditTab', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(true)
  })

  it('adds and activates a node-edit tab', () => {
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
})
