import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { mockTaskState } from '@/mock/taskState.mock'
import { mockRecentTasks } from '@/mock/workspace.mock'

describe('taskStore panel lifecycle', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(true)
    useUiStore.setState({ rightCollapsed: false, leftCollapsed: false })
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

  it('selectTask collapses the left panel and expands the right panel in mock mode', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_MOCK_DATA', 'true')

    const { useTaskStore: mockTaskStore } = await import('@/store/taskStore')
    const { useUiStore: mockUiStore } = await import('@/store/uiStore')
    const { useRightPanelStore: mockRightPanelStore } = await import('@/store/rightPanelStore')

    mockUiStore.setState({ leftCollapsed: false, rightCollapsed: true })
    mockRightPanelStore.getState().reset(false)
    mockTaskStore.setState({
      activeTask: null,
      activeTaskState: null,
      recentTasks: mockRecentTasks,
      availableTasks: [],
      projectTasks: {},
    })

    await mockTaskStore.getState().selectTask('recent_pipe_001')

    expect(mockTaskStore.getState().activeTask).not.toBeNull()
    expect(mockUiStore.getState().leftCollapsed).toBe(true)
    expect(mockUiStore.getState().rightCollapsed).toBe(false)
    expect(mockRightPanelStore.getState().activeTabId).toBe('task')
  })

  it('clearActiveTask collapses the right panel and removes the Task tab', () => {
    useTaskStore.getState().clearActiveTask()

    expect(useTaskStore.getState().activeTask).toBeNull()
    expect(useUiStore.getState().rightCollapsed).toBe(true)
    expect(useRightPanelStore.getState().tabs.map((tab) => tab.id)).toEqual(['chat', 'standards'])
    expect(useRightPanelStore.getState().activeTabId).toBe('chat')
  })
})
