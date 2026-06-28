import { beforeEach, describe, expect, it } from 'vitest'

import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { mockTaskState } from '@/mock/taskState.mock'

describe('taskStore right panel lifecycle', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(true)
    useUiStore.setState({ rightCollapsed: false })
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: mockTaskState,
    })
  })

  it('clearActiveTask collapses the right panel and removes the Task tab', () => {
    useTaskStore.getState().clearActiveTask()

    expect(useTaskStore.getState().activeTask).toBeNull()
    expect(useUiStore.getState().rightCollapsed).toBe(true)
    expect(useRightPanelStore.getState().tabs.map((tab) => tab.id)).toEqual(['chat', 'standards'])
    expect(useRightPanelStore.getState().activeTabId).toBe('chat')
  })
})
