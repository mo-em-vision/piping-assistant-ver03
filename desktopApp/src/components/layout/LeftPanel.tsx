import { useEffect, useState, type MouseEvent } from 'react'

import { useChatStore } from '@/store/chatStore'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { TaskContextMenu } from '@/components/tasks/TaskContextMenu'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import type { TaskSummary } from '@/types/frontend/workspace'

import { PanelSection } from './PanelSection'
import './SidePanel.css'

const STRAIGHT_PIPE_TASK_CONFIRMATION =
  'Is the pipe wall thickness you would like to calculate for a straight section of pipe? Non-straight sections (fittings, bends) are not yet supported.'

function TaskListItem({
  task,
  isActive,
  onSelect,
  onContextMenu,
  disabled,
}: {
  task: TaskSummary
  isActive: boolean
  onSelect: () => void
  onContextMenu?: (task: TaskSummary, event: MouseEvent) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      className={`list-button${isActive ? ' list-button--active' : ''}`}
      onClick={onSelect}
      disabled={disabled}
      onContextMenu={
        onContextMenu
          ? (event) => {
              event.preventDefault()
              onContextMenu(task, event)
            }
          : undefined
      }
    >
      <span className="list-button__name">{task.name}</span>
      <span className="list-button__meta">{task.description}</span>
      {task.status ? <span className="list-button__badge">{task.status.replace('_', ' ')}</span> : null}
    </button>
  )
}

export function LeftPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const availableTasks = useTaskStore((state) => state.availableTasks)
  const recentTasks = useTaskStore((state) => state.recentTasks)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const createTask = useTaskStore((state) => state.createTask)
  const selectTask = useTaskStore((state) => state.selectTask)
  const deleteTask = useTaskStore((state) => state.deleteTask)
  const clearActiveTask = useTaskStore((state) => state.clearActiveTask)
  const loadWorkspace = useTaskStore((state) => state.loadWorkspace)
  const [contextMenu, setContextMenu] = useState<{
    task: TaskSummary
    x: number
    y: number
  } | null>(null)
  const projects = useProjectStore((state) => state.projects)
  const activeProjectId = useProjectStore((state) => state.activeProjectId)
  const projectLoading = useProjectStore((state) => state.loading)
  const projectUserError = useProjectStore((state) => state.userError)
  const selectProject = useProjectStore((state) => state.selectProject)
  const createProject = useProjectStore((state) => state.createProject)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const toggleLeftCollapsed = useUiStore((state) => state.toggleLeftCollapsed)

  const defaultWorkflow = availableTasks[0]
  const busy = loading || projectLoading

  const handleCreateWorkflow = (workflowId: string) => {
    if (workflowId === 'pipe_wall_thickness_design') {
      const confirmed = window.confirm(STRAIGHT_PIPE_TASK_CONFIRMATION)
      if (!confirmed) {
        return
      }
    }
    void createTask(workflowId)
  }

  const handleProjectSelect = (projectId: string) => {
    void selectProject(projectId).then(() => {
      clearActiveTask()
      void loadWorkspace()
      void loadMessages()
    })
  }

  const handleCreateProject = () => {
    const name = window.prompt('Project name')
    if (!name?.trim()) {
      return
    }
    void createProject(name.trim()).then(() => {
      clearActiveTask()
      void loadWorkspace()
      void loadMessages()
    })
  }

  const openTaskContextMenu = (task: TaskSummary, x: number, y: number) => {
    setContextMenu({ task, x, y })
  }

  const handleDeleteTask = (task: TaskSummary) => {
    void deleteTask(task.id)
  }

  useEffect(() => {
    if (!contextMenu) {
      return
    }

    const closeMenu = () => {
      setContextMenu(null)
    }

    window.addEventListener('resize', closeMenu)
    return () => {
      window.removeEventListener('resize', closeMenu)
    }
  }, [contextMenu])

  return (
    <aside className="side-panel side-panel--left">
      <header className="side-panel__header">
        <h2 className="side-panel__title">Navigation</h2>
        <button
          type="button"
          className="side-panel__collapse"
          onClick={toggleLeftCollapsed}
          aria-label="Collapse left panel"
          title="Collapse panel"
        >
          ‹
        </button>
      </header>

      <div className="side-panel__content">
        {projectUserError ? (
          <ErrorBanner
            error={projectUserError}
            compact
            onRetry={() => {
              void loadWorkspace()
            }}
          />
        ) : null}
        {userError ? (
          <ErrorBanner
            error={userError}
            compact
            onRetry={() => {
              void loadWorkspace()
            }}
          />
        ) : null}

        <PanelSection
          title="Projects"
          action={
            <button type="button" className="panel-section__action" onClick={handleCreateProject} disabled={busy}>
              + New
            </button>
          }
        >
          {projects.length === 0 ? (
            <p className="side-panel__hint">No projects yet. Create one to persist tasks and chat.</p>
          ) : (
            projects.map((project) => (
              <button
                key={project.id}
                type="button"
                className={`list-button${activeProjectId === project.id ? ' list-button--active' : ''}`}
                disabled={busy}
                onClick={() => handleProjectSelect(project.id)}
              >
                <span className="list-button__name">{project.name}</span>
                <span className="list-button__meta">
                  {project.taskCount} tasks
                  {project.updatedAt ? ` · updated ${project.updatedAt.slice(0, 10)}` : ''}
                </span>
              </button>
            ))
          )}
        </PanelSection>

        <PanelSection title="Create task">
          <button
            type="button"
            className="create-task-button"
            disabled={busy || !defaultWorkflow}
            onClick={() => {
              if (defaultWorkflow) {
                handleCreateWorkflow(defaultWorkflow.id)
              }
            }}
          >
            + New engineering task
          </button>
        </PanelSection>

        <PanelSection title="Available tasks">
          {availableTasks.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              isActive={activeTask?.id === task.id}
              disabled={busy}
              onSelect={() => {
                handleCreateWorkflow(task.id)
              }}
            />
          ))}
        </PanelSection>

        <PanelSection title="Recent tasks">
          {recentTasks.length === 0 ? (
            <p className="side-panel__hint">No recent tasks in this project.</p>
          ) : (
            recentTasks.map((task) => (
              <TaskListItem
                key={task.id}
                task={task}
                isActive={activeTask?.id === task.id}
                disabled={busy}
                onSelect={() => {
                  void selectTask(task.id)
                }}
                onContextMenu={(selectedTask, event) => {
                  openTaskContextMenu(selectedTask, event.clientX, event.clientY)
                }}
              />
            ))
          )}
        </PanelSection>
      </div>

      {contextMenu ? (
        <TaskContextMenu
          task={contextMenu.task}
          x={contextMenu.x}
          y={contextMenu.y}
          onDelete={handleDeleteTask}
          onClose={() => {
            setContextMenu(null)
          }}
        />
      ) : null}
    </aside>
  )
}
