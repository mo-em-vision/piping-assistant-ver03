import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeftPanel } from '@/components/layout/LeftPanel'
import { mockAvailableTasks, mockProjects, mockRecentTasks } from '@/mock/workspace.mock'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

vi.mock('@/utils/confirmTaskDeletion', () => ({
  confirmTaskDeletion: vi.fn(() => true),
}))

vi.mock('@/utils/confirmProjectDeletion', () => ({
  confirmProjectDeletion: vi.fn(() => true),
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

  it('shows new project action when no projects exist', () => {
    render(<LeftPanel />)

    expect(screen.getByRole('button', { name: 'Create new project' })).toBeInTheDocument()
    expect(screen.getByText('No projects yet.')).toBeInTheDocument()
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

    expect(screen.getByText(/Refinery Expansion/i)).toBeInTheDocument()
    expect(screen.queryByText('Default')).not.toBeInTheDocument()
  })

  it('calls deleteTask when recycling bin is clicked on a recent task', async () => {
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

  it('calls deleteTask when recycling bin is clicked on a project task', async () => {
    const user = userEvent.setup()
    const deleteTask = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })
    useTaskStore.setState({
      projectTasks: {
        [mockProjects[0].id]: mockRecentTasks.slice(0, 1),
      },
      deleteTask,
    })

    render(<LeftPanel />)

    await user.click(screen.getByRole('button', { name: /delete pipe thickness — line 200/i }))
    await waitFor(() => {
      expect(deleteTask).toHaveBeenCalledWith('recent_pipe_001', 'proj_refinery')
    })
  })

  it('does not show a separate Tasks section', () => {
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })

    render(<LeftPanel />)

    expect(screen.getByRole('button', { name: 'Create new task' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tasks' })).not.toBeInTheDocument()
    expect(screen.queryByText('Create new task', { selector: '.create-task-button' })).not.toBeInTheDocument()
  })

  it('calls deleteProject when delete action is clicked on a project', async () => {
    const user = userEvent.setup()
    const deleteProject = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
      deleteProject,
    })

    render(<LeftPanel />)

    await user.click(screen.getByRole('button', { name: /delete refinery expansion/i }))
    await waitFor(() => {
      expect(deleteProject).toHaveBeenCalledWith(mockProjects[0].id)
    })
  })

  it('opens delete task menu on right-click for a recent task', async () => {
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

    fireEvent.contextMenu(screen.getByText('Pipe Thickness — Line 200'))
    fireEvent.click(screen.getByRole('menuitem', { name: /delete task/i }))

    await waitFor(() => {
      expect(deleteTask).toHaveBeenCalledWith('recent_pipe_001', 'proj_refinery')
    })
  })

  it('opens delete project menu on right-click for a project name', async () => {
    const deleteProject = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
      deleteProject,
    })

    render(<LeftPanel />)

    fireEvent.contextMenu(screen.getByText('Refinery Expansion'))
    fireEvent.click(screen.getByRole('menuitem', { name: /delete project/i }))

    await waitFor(() => {
      expect(deleteProject).toHaveBeenCalledWith(mockProjects[0].id)
    })
  })

  it('opens rename dialog and calls renameProject on save', async () => {
    const user = userEvent.setup()
    const renameProject = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
      renameProject,
    })

    render(<LeftPanel />)

    fireEvent.contextMenu(screen.getByText('Refinery Expansion'))
    fireEvent.click(screen.getByRole('menuitem', { name: /rename project/i }))

    expect(screen.getByRole('heading', { name: 'Rename project' })).toBeInTheDocument()

    const input = screen.getByLabelText('Project name')
    await user.clear(input)
    await user.type(input, 'Renamed Refinery')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(renameProject).toHaveBeenCalledWith(mockProjects[0].id, 'Renamed Refinery')
    })
  })

  it('opens rename dialog and calls renameTask on save', async () => {
    const user = userEvent.setup()
    const renameTask = vi.fn().mockResolvedValue(undefined)
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0].id,
    })
    useTaskStore.setState({
      recentTasks: mockRecentTasks,
      renameTask,
    })

    render(<LeftPanel />)

    fireEvent.contextMenu(screen.getByText('Pipe Thickness — Line 200'))
    fireEvent.click(screen.getByRole('menuitem', { name: /rename task/i }))

    expect(screen.getByRole('heading', { name: 'Rename task' })).toBeInTheDocument()

    const input = screen.getByLabelText('Task name')
    await user.clear(input)
    await user.type(input, 'Line 200 Custom')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(renameTask).toHaveBeenCalledWith('recent_pipe_001', 'Line 200 Custom', 'proj_refinery')
    })
  })
})
