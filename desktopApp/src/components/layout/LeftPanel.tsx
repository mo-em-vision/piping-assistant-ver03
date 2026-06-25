import { useState } from 'react'

import { useChatStore } from '@/store/chatStore'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { CreateProjectDialog } from '@/components/projects/CreateProjectDialog'
import { ProjectGroup } from '@/components/projects/ProjectGroup'
import { CreateTaskDialog } from '@/components/tasks/CreateTaskDialog'
import { RecentTaskRow } from '@/components/tasks/RecentTaskRow'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'

import { PanelSection } from './PanelSection'
import './SidePanel.css'

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

  const projects = useProjectStore((state) => state.projects)
  const activeProjectId = useProjectStore((state) => state.activeProjectId)
  const projectLoading = useProjectStore((state) => state.loading)
  const projectUserError = useProjectStore((state) => state.userError)
  const selectProject = useProjectStore((state) => state.selectProject)
  const createProject = useProjectStore((state) => state.createProject)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const toggleLeftCollapsed = useUiStore((state) => state.toggleLeftCollapsed)

  const [expandedProjectIds, setExpandedProjectIds] = useState<Set<string>>(() => new Set())
  const [createProjectOpen, setCreateProjectOpen] = useState(false)
  const [createTaskOpen, setCreateTaskOpen] = useState(false)

  const busy = loading || projectLoading
  const hasProjects = projects.length > 0
  const visibleProjects = projects.filter((project) => project.id !== 'default')
  const canCreateTask = hasProjects && Boolean(activeProjectId)

  const handleProjectSelect = (projectId: string) => {
    setExpandedProjectIds((current) => new Set(current).add(projectId))
    void selectProject(projectId).then(() => {
      clearActiveTask()
      void loadWorkspace()
      void loadMessages()
    })
  }

  const handleCreateProject = (name: string) => {
    void createProject(name).then(() => {
      setCreateProjectOpen(false)
      clearActiveTask()
      void loadWorkspace()
      void loadMessages()
    })
  }

  const handleToggleProject = (projectId: string) => {
    setExpandedProjectIds((current) => {
      const next = new Set(current)
      if (next.has(projectId)) {
        next.delete(projectId)
      } else {
        next.add(projectId)
      }
      return next
    })
  }

  const handleCreateTask = (workflowId: string) => {
    setCreateTaskOpen(false)
    void createTask(workflowId)
  }

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

        <PanelSection title="Projects">
          {visibleProjects.length === 0 ? (
            <button
              type="button"
              className="list-button list-button--cta"
              disabled={busy}
              onClick={() => setCreateProjectOpen(true)}
            >
              <span className="list-button__name">Create new project</span>
            </button>
          ) : (
            <div className="left-panel__projects">
              {visibleProjects.map((project) => {
                const isActive = activeProjectId === project.id
                const expanded = expandedProjectIds.has(project.id) || isActive
                return (
                  <ProjectGroup
                    key={project.id}
                    project={project}
                    isActive={isActive}
                    activeTaskId={activeTask?.id ?? null}
                    expanded={expanded}
                    disabled={busy}
                    onToggle={() => handleToggleProject(project.id)}
                    onSelectProject={() => handleProjectSelect(project.id)}
                    onSelectTask={(taskId, projectId) => {
                      void selectTask(taskId, projectId)
                    }}
                  />
                )
              })}
              <button
                type="button"
                className="list-button list-button--cta"
                disabled={busy}
                onClick={() => setCreateProjectOpen(true)}
              >
                <span className="list-button__name">Create new project</span>
              </button>
            </div>
          )}
        </PanelSection>

        {visibleProjects.length > 0 ? (
          <PanelSection title="Tasks">
            <button
              type="button"
              className="create-task-button"
              disabled={busy || !canCreateTask}
              onClick={() => setCreateTaskOpen(true)}
            >
              Create new task
            </button>
          </PanelSection>
        ) : null}

        <PanelSection title="Recent tasks">
          {recentTasks.length === 0 ? (
            <p className="side-panel__hint">No recent tasks yet.</p>
          ) : (
            <div className="left-panel__recent-tasks">
              {recentTasks.map((task) => (
                <RecentTaskRow
                  key={`${task.projectId ?? 'task'}-${task.id}`}
                  task={task}
                  isActive={activeTask?.id === task.id}
                  disabled={busy}
                  onSelect={() => {
                    void selectTask(task.id, task.projectId)
                  }}
                  onDelete={() => {
                    void deleteTask(task.id, task.projectId)
                  }}
                />
              ))}
            </div>
          )}
        </PanelSection>
      </div>

      <CreateProjectDialog
        open={createProjectOpen}
        busy={busy}
        onConfirm={handleCreateProject}
        onCancel={() => setCreateProjectOpen(false)}
      />

      <CreateTaskDialog
        open={createTaskOpen}
        tasks={availableTasks}
        busy={busy}
        onSelect={handleCreateTask}
        onCancel={() => setCreateTaskOpen(false)}
      />
    </aside>
  )
}
