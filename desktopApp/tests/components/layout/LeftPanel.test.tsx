import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeftPanel } from '@/components/layout/LeftPanel'
import { mockAvailableTasks, mockProjects, mockRecentTasks } from '@/mock/workspace.mock'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

vi.mock('@/utils/confirmTaskDeletion', () => ({
  confirmTaskDeletion: vi.fn(() => true),
}))

describe('LeftPanel', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_MOCK_DATA', 'true')
    useProjectStore.setState({
      projects: [],
      activeProjectId: null,
      loading: false,
      userError: null,
    })
    useTaskStore.setState({
      availableTasks: mockAvailableTasks,
      recentTasks: [],
      projectTasks: {},
      activeTask: null,
      activeTaskState: null,
      loading: false,
      userError: null,
    })
  })

  it('shows create new project when no projects exist', () => {
    render(<LeftPanel />)

    expect(screen.getByRole('button', { name: 'Create new project' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create new task' })).not.toBeInTheDocument()
  })

  it('opens create task dialog and filters workflows', async () => {
    const user = userEvent.setup()
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })
    useTaskStore.setState({ recentTasks: mockRecentTasks })

    render(<LeftPanel />)

    await user.click(screen.getByRole('button', { name: 'Create new task' }))
    expect(screen.getByRole('heading', { name: 'Create new task' })).toBeInTheDocument()

    const search = screen.getByPlaceholderText(/search workflows/i)
    await user.type(search, 'flange')
    expect(screen.getByText('Flange Selection')).toBeInTheDocument()
    expect(screen.queryByText('Tank Design')).not.toBeInTheDocument()
  })

  it('shows minimal recent tasks with title and status', () => {
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })
    useTaskStore.setState({ recentTasks: mockRecentTasks })

    render(<LeftPanel />)

    expect(screen.getByText('Pipe Thickness — Line 200')).toBeInTheDocument()
    expect(screen.getByText('in progress')).toBeInTheDocument()
  })

  it('filters legacy default project from the list', () => {
    useProjectStore.setState({
      projects: [
        ...mockProjects,
        { id: 'default', name: 'Default', taskCount: 1, updatedAt: '2026-01-01' },
      ],
      activeProjectId: mockProjects[0].id,
    })

    render(<LeftPanel />)

    expect(screen.getByText('Refinery Expansion')).toBeInTheDocument()
    expect(screen.queryByText('Default')).not.toBeInTheDocument()
  })

  it('calls deleteTask when recycling bin is clicked', async () => {
    const user = userEvent.setup()
    const deleteTask = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })
    useTaskStore.setState({
      recentTasks: mockRecentTasks,
      deleteTask,
    })

    render(<LeftPanel />)

    await user.click(screen.getByRole('button', { name: /delete pipe thickness/i }))
    await waitFor(() => {
      expect(deleteTask).toHaveBeenCalledWith('recent_pipe_001', 'proj_refinery')
    })
  })
})
