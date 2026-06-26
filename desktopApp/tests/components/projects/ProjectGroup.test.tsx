import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ProjectGroup, projectLabel } from '@/components/projects/ProjectGroup'
import { useTaskStore } from '@/store/taskStore'

describe('projectLabel', () => {
  const project = {
    id: 'proj_test',
    name: 'Test Project',
    taskCount: 1,
    updatedAt: '2026-01-01',
  }

  it('uses loaded count of zero when tasks are loaded', () => {
    expect(projectLabel(project, 0, true)).toBe('Test Project (0 Tasks)')
  })

  it('uses stored task count when tasks are not loaded', () => {
    expect(projectLabel(project, 0, false)).toBe('Test Project (1 Task)')
  })

  it('uses loaded count when tasks are loaded', () => {
    expect(projectLabel({ ...project, taskCount: 5 }, 2, true)).toBe('Test Project (2 Tasks)')
  })
})

describe('ProjectGroup', () => {
  beforeEach(() => {
    useTaskStore.setState({ projectTasks: {} })
  })

  const baseProps = {
    project: {
      id: 'proj_test',
      name: 'Test Project',
      taskCount: 1,
      updatedAt: '2026-01-01',
    },
    isActive: false,
    activeTaskId: null,
    expanded: false,
    onToggle: vi.fn(),
    onSelectProject: vi.fn(),
    onSelectTask: vi.fn(),
    onDeleteTask: vi.fn(),
    onDeleteProject: vi.fn(),
    onRenameProject: vi.fn(),
    onRenameTask: vi.fn(),
    onProjectContextMenu: vi.fn(),
    onTaskContextMenu: vi.fn(),
  }

  it('shows stored task count when tasks are not loaded', () => {
    render(<ProjectGroup {...baseProps} />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('(1 Task)')).toBeInTheDocument()
  })

  it('shows loaded task count including zero', () => {
    useTaskStore.setState({
      projectTasks: {
        proj_test: [],
      },
    })

    render(<ProjectGroup {...baseProps} expanded />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('(0 Tasks)')).toBeInTheDocument()
  })

  it('calls onProjectContextMenu when project header is right-clicked', () => {
    const onProjectContextMenu = vi.fn()
    const { container } = render(
      <ProjectGroup {...baseProps} onProjectContextMenu={onProjectContextMenu} />,
    )

    fireEvent.contextMenu(container.querySelector('.project-group__header')!)
    expect(onProjectContextMenu).toHaveBeenCalledTimes(1)
  })

  it('calls onTaskContextMenu when task row is right-clicked', () => {
    const onTaskContextMenu = vi.fn()
    useTaskStore.setState({
      projectTasks: {
        proj_test: [
          {
            id: 'task_1',
            name: 'Sample Task',
            description: '',
            discipline: 'Piping',
            status: 'in_progress',
          },
        ],
      },
    })

    const { container } = render(<ProjectGroup {...baseProps} expanded onTaskContextMenu={onTaskContextMenu} />)

    fireEvent.contextMenu(container.querySelector('.project-group__task-row')!)
    expect(onTaskContextMenu).toHaveBeenCalledTimes(1)
  })

  it('calls onDeleteProject when delete action is clicked', async () => {
    const user = userEvent.setup()
    const onDeleteProject = vi.fn()
    render(<ProjectGroup {...baseProps} onDeleteProject={onDeleteProject} />)

    await user.click(screen.getByRole('button', { name: /delete test project/i }))
    expect(onDeleteProject).toHaveBeenCalledWith('proj_test')
  })

  it('calls onRenameProject when edit action is clicked', async () => {
    const user = userEvent.setup()
    const onRenameProject = vi.fn()
    render(<ProjectGroup {...baseProps} onRenameProject={onRenameProject} />)

    await user.click(screen.getByRole('button', { name: /rename test project/i }))
    expect(onRenameProject).toHaveBeenCalledWith(baseProps.project)
  })
})
