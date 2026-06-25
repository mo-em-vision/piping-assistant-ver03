import { useEffect, useState } from 'react'

import { useTaskStore } from '@/store/taskStore'
import type { ProjectSummary } from '@/types/frontend/workspace'

import './ProjectGroup.css'

function formatTaskCount(count: number): string {
  return count === 1 ? '1 Task' : `${count} Tasks`
}

function projectLabel(project: ProjectSummary, loadedTaskCount: number): string {
  const count = loadedTaskCount > 0 ? loadedTaskCount : project.taskCount
  return `${project.name} (${formatTaskCount(count)})`
}

interface ProjectGroupProps {
  project: ProjectSummary
  isActive: boolean
  activeTaskId: string | null
  expanded: boolean
  disabled?: boolean
  onToggle: () => void
  onSelectProject: () => void
  onSelectTask: (taskId: string, projectId: string) => void
  onDeleteTask: (taskId: string, projectId: string) => void
  onCreateTask?: () => void
}

export function ProjectGroup({
  project,
  isActive,
  activeTaskId,
  expanded,
  disabled,
  onToggle,
  onSelectProject,
  onSelectTask,
  onDeleteTask,
  onCreateTask,
}: ProjectGroupProps) {
  const projectTasks = useTaskStore((state) => state.projectTasks[project.id])
  const loadProjectTasks = useTaskStore((state) => state.loadProjectTasks)
  const [loadingTasks, setLoadingTasks] = useState(false)

  useEffect(() => {
    if (!expanded || projectTasks) {
      return
    }
    setLoadingTasks(true)
    void loadProjectTasks(project.id).finally(() => {
      setLoadingTasks(false)
    })
  }, [expanded, loadProjectTasks, project.id, projectTasks])

  const tasks = projectTasks ?? []

  return (
    <div className="project-group">
      <div className="project-group__header">
        <button
          type="button"
          className="project-group__chevron"
          onClick={onToggle}
          disabled={disabled}
          aria-expanded={expanded}
          aria-label={expanded ? `Collapse ${project.name}` : `Expand ${project.name}`}
        >
          {expanded ? '▾' : '▸'}
        </button>
        <button
          type="button"
          className={`project-group__title${isActive ? ' project-group__title--active' : ''}`}
          onClick={onSelectProject}
          disabled={disabled}
        >
          <span className="project-group__name">{projectLabel(project, tasks.length)}</span>
        </button>
      </div>
      {expanded ? (
        <div className="project-group__tasks">
          {loadingTasks && tasks.length === 0 ? (
            <p className="project-group__hint">Loading tasks…</p>
          ) : tasks.length === 0 && !isActive ? (
            <p className="project-group__hint">No tasks in this project yet.</p>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className={`project-group__task-row${activeTaskId === task.id ? ' project-group__task-row--active' : ''}`}
              >
                <button
                  type="button"
                  className="project-group__task-select"
                  disabled={disabled}
                  onClick={() => onSelectTask(task.id, project.id)}
                >
                  <span className="project-group__task-name">{task.name}</span>
                  {task.status ? (
                    <span className="project-group__task-status">
                      {task.status.replace(/_/g, ' ')}
                    </span>
                  ) : null}
                </button>
                <button
                  type="button"
                  className="project-group__task-delete"
                  disabled={disabled}
                  onClick={(event) => {
                    event.stopPropagation()
                    onDeleteTask(task.id, project.id)
                  }}
                  aria-label={`Delete ${task.name}`}
                  title="Delete task"
                >
                  🗑
                </button>
              </div>
            ))
          )}
          {isActive && onCreateTask ? (
            <button
              type="button"
              className="project-group__new-task"
              disabled={disabled}
              aria-label="Create new task"
              onClick={onCreateTask}
            >
              Create new task
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
