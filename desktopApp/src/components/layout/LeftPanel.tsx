import { useState, type MouseEvent } from 'react'

import { RenameDialog } from '@/components/common/RenameDialog'
import { useChatStore } from '@/store/chatStore'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { CreateProjectDialog } from '@/components/projects/CreateProjectDialog'
import { ProjectGroup } from '@/components/projects/ProjectGroup'
import { CreateTaskDialog } from '@/components/tasks/CreateTaskDialog'
import { RecentTaskRow } from '@/components/tasks/RecentTaskRow'
import { SidePanelContextMenu } from '@/components/layout/SidePanelContextMenu'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import type { ProjectSummary, TaskSummary } from '@/types/frontend/workspace'

import { PanelSection } from './PanelSection'
import './SidePanel.css'

type ContextMenuState =
  | {
      type: 'project'
      project: ProjectSummary
      x: number
      y: number
    }
  | {
      type: 'task'
      task: TaskSummary
      projectId?: string
      x: number
      y: number
    }
  | null

type RenameTarget =
  | {
      type: 'project'
      id: string
      name: string
    }
  | {
      type: 'task'
      id: string
      name: string
      projectId?: string
    }
  | null

export function LeftPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const availableTasks = useTaskStore((state) => state.availableTasks)
  const recentTasks = useTaskStore((state) => state.recentTasks)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const createTask = useTaskStore((state) => state.createTask)
  const selectTask = useTaskStore((state) => state.selectTask)
  const deleteTask = useTaskStore((state) => state.deleteTask)
  const renameTask = useTaskStore((state) => state.renameTask)
  const clearActiveTask = useTaskStore((state) => state.clearActiveTask)
  const loadWorkspace = useTaskStore((state) => state.loadWorkspace)

  const projects = useProjectStore((state) => state.projects)
  const activeProjectId = useProjectStore((state) => state.activeProjectId)
  const projectLoading = useProjectStore((state) => state.loading)
  const projectUserError = useProjectStore((state) => state.userError)
  const selectProject = useProjectStore((state) => state.selectProject)
  const createProject = useProjectStore((state) => state.createProject)
  const deleteProject = useProjectStore((state) => state.deleteProject)
  const renameProject = useProjectStore((state) => state.renameProject)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const toggleLeftCollapsed = useUiStore((state) => state.toggleLeftCollapsed)
  const createTaskDialog = useUiStore((state) => state.createTaskDialog)
  const openCreateTaskDialog = useUiStore((state) => state.openCreateTaskDialog)
  const closeCreateTaskDialog = useUiStore((state) => state.closeCreateTaskDialog)

  const [expandedProjectIds, setExpandedProjectIds] = useState<Set<string>>(() => {
    const initialActiveId = useProjectStore.getState().activeProjectId
    return initialActiveId ? new Set([initialActiveId]) : new Set()
  })
  const [createProjectOpen, setCreateProjectOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<ContextMenuState>(null)
  const [renameTarget, setRenameTarget] = useState<RenameTarget>(null)

  const busy = loading || projectLoading
  const visibleProjects = projects.filter((project) => project.id !== 'default')

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
      const newProjectId = useProjectStore.getState().activeProjectId
      if (newProjectId) {
        setExpandedProjectIds((current) => new Set(current).add(newProjectId))
      }
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
    closeCreateTaskDialog()
    void createTask(workflowId)
  }

  const openProjectContextMenu = (event: MouseEvent, project: ProjectSummary) => {
    event.preventDefault()
    event.stopPropagation()
    setContextMenu({
      type: 'project',
      project,
      x: event.clientX,
      y: event.clientY,
    })
  }

  const openTaskContextMenu = (
    event: MouseEvent,
    task: TaskSummary,
    projectId?: string,
  ) => {
    event.preventDefault()
    event.stopPropagation()
    setContextMenu({
      type: 'task',
      task,
      projectId,
      x: event.clientX,
      y: event.clientY,
    })
  }

  const openRenameProject = (project: ProjectSummary) => {
    setRenameTarget({
      type: 'project',
      id: project.id,
      name: project.name,
    })
  }

  const openRenameTask = (task: TaskSummary, projectId?: string) => {
    setRenameTarget({
      type: 'task',
      id: task.id,
      name: task.name,
      projectId: projectId ?? task.projectId,
    })
  }

  const handleRenameConfirm = (name: string) => {
    if (!renameTarget) {
      return
    }
    if (renameTarget.type === 'project') {
      void renameProject(renameTarget.id, name).then(() => {
        setRenameTarget(null)
      })
      return
    }
    void renameTask(renameTarget.id, name, renameTarget.projectId).then(() => {
      setRenameTarget(null)
    })
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

        <PanelSection
          title="Projects"
          className="panel-section--projects"
          action={
            <button
              type="button"
              className="panel-section__header-link"
              disabled={busy}
              onClick={() => setCreateProjectOpen(true)}
              aria-label="Create new project"
            >
              Create new project
            </button>
          }
        >
          {visibleProjects.length === 0 ? (
            <p className="side-panel__hint">No projects yet.</p>
          ) : (
            <div className="left-panel__projects">
              {visibleProjects.map((project) => {
                const isActive = activeProjectId === project.id
                const expanded = expandedProjectIds.has(project.id)
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
                    onDeleteTask={(taskId, projectId) => {
                      void deleteTask(taskId, projectId)
                    }}
                    onDeleteProject={(projectId) => {
                      void deleteProject(projectId).then(() => {
                        setExpandedProjectIds((current) => {
                          const next = new Set(current)
                          next.delete(projectId)
                          return next
                        })
                        void loadMessages()
                      })
                    }}
                    onRenameProject={openRenameProject}
                    onRenameTask={openRenameTask}
                    onProjectContextMenu={openProjectContextMenu}
                    onTaskContextMenu={openTaskContextMenu}
                    onCreateTask={
                      isActive
                        ? () => {
                            openCreateTaskDialog()
                          }
                        : undefined
                    }
                  />
                )
              })}
            </div>
          )}
        </PanelSection>

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
                  onRename={openRenameTask}
                  onContextMenu={openTaskContextMenu}
                />
              ))}
            </div>
          )}
        </PanelSection>
      </div>

      {contextMenu?.type === 'project' ? (
        <SidePanelContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          ariaLabel={`Actions for ${contextMenu.project.name}`}
          onClose={() => setContextMenu(null)}
          items={[
            {
              label: 'Rename project',
              onClick: () => {
                openRenameProject(contextMenu.project)
              },
            },
            {
              label: 'Delete project',
              danger: true,
              onClick: () => {
                void deleteProject(contextMenu.project.id).then(() => {
                  setExpandedProjectIds((current) => {
                    const next = new Set(current)
                    next.delete(contextMenu.project.id)
                    return next
                  })
                  void loadMessages()
                })
              },
            },
          ]}
        />
      ) : null}

      {contextMenu?.type === 'task' ? (
        <SidePanelContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          ariaLabel={`Actions for ${contextMenu.task.name}`}
          onClose={() => setContextMenu(null)}
          items={[
            {
              label: 'Rename task',
              onClick: () => {
                openRenameTask(contextMenu.task, contextMenu.projectId ?? contextMenu.task.projectId)
              },
            },
            {
              label: 'Delete task',
              danger: true,
              onClick: () => {
                void deleteTask(contextMenu.task.id, contextMenu.projectId ?? contextMenu.task.projectId)
              },
            },
          ]}
        />
      ) : null}

      <RenameDialog
        open={renameTarget !== null}
        title={renameTarget?.type === 'project' ? 'Rename project' : 'Rename task'}
        label={renameTarget?.type === 'project' ? 'Project name' : 'Task name'}
        initialName={renameTarget?.name ?? ''}
        busy={busy}
        onConfirm={handleRenameConfirm}
        onCancel={() => setRenameTarget(null)}
      />

      <CreateProjectDialog
        open={createProjectOpen}
        busy={busy}
        onConfirm={handleCreateProject}
        onCancel={() => setCreateProjectOpen(false)}
      />

      <CreateTaskDialog
        open={createTaskDialog.open}
        preselectedWorkflowId={createTaskDialog.preselectedWorkflowId}
        tasks={availableTasks}
        busy={busy}
        onSelect={handleCreateTask}
        onCancel={closeCreateTaskDialog}
      />
    </aside>
  )
}
