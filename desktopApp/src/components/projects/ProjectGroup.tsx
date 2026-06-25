import { useEffect, useState } from 'react'

import { useTaskStore } from '@/store/taskStore'
import type { ProjectSummary } from '@/types/frontend/workspace'

import './ProjectGroup.css'

interface ProjectGroupProps {
  project: ProjectSummary
  isActive: boolean
  activeTaskId: string | null
  expanded: boolean
  disabled?: boolean
  onToggle: () => void
  onSelectProject: () => void
  onSelectTask: (taskId: string, projectId: string) => void
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
    <div className={`project-group${isActive ? ' project-group--active' : ''}`}>
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
          <span className="project-group__name">{project.name}</span>
          <span className="project-group__meta">{project.taskCount} tasks</span>
        </button>
      </div>
      {expanded ? (
        <div className="project-group__tasks">
          {loadingTasks && tasks.length === 0 ? (
            <p className="project-group__hint">Loading tasks…</p>
          ) : tasks.length === 0 ? (
            <p className="project-group__hint">No tasks in this project yet.</p>
          ) : (
            tasks.map((task) => (
              <button
                key={task.id}
                type="button"
                className={`project-group__task${activeTaskId === task.id ? ' project-group__task--active' : ''}`}
                disabled={disabled}
                onClick={() => onSelectTask(task.id, project.id)}
              >
                <span className="project-group__task-name">{task.name}</span>
                {task.status ? (
                  <span className="project-group__task-status">{task.status.replace(/_/g, ' ')}</span>
                ) : null}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  )
}
