import { startTransition } from 'react'
import { create } from 'zustand'

import { applyOptimisticParameterSubmit } from '@/components/workflow/optimisticWorkflowTransition'
import { formatEngineeringDisplayValue } from '@/utils/engineeringDisplay'
import { inputApi } from '@/services/api/inputApi'
import { taskApi } from '@/services/api/taskApi'
import { toNavTaskSummary, workflowToSummary } from '@/services/api/responseParser'
import { getActiveSessionId, useProjectStore } from '@/store/projectStore'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useUiStore } from '@/store/uiStore'
import { toUserFacingError } from '@/types/backend/errors'
import { confirmTaskDeletion } from '@/utils/confirmTaskDeletion'
import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'
import type { UserFacingError } from '@/types/frontend/userError'
import type { TaskStateDto, TaskSummaryDto } from '@/types/backend/api'
import type { TaskSummary } from '@/types/frontend/workspace'

import {
  mockAvailableTasks,
  mockRecentTasks,
} from '@/mock/workspace.mock'
import { mockTaskState } from '@/mock/taskState.mock'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface TaskStoreState {
  sessionId: string | null
  loading: boolean
  userError: UserFacingError | null
  activeTask: TaskSummary | null
  activeTaskState: TaskStateDto | null
  availableTasks: TaskSummary[]
  recentTasks: TaskSummary[]
  projectTasks: Record<string, TaskSummary[]>
  loadWorkspace: () => Promise<void>
  loadProjectTasks: (projectId: string) => Promise<void>
  loadRecentTasksGlobal: () => Promise<void>
  selectTask: (taskId: string, projectId?: string) => Promise<void>
  createTask: (workflowId: string) => Promise<void>
  clearActiveTask: () => void
  deleteTask: (taskId: string, projectId?: string) => Promise<void>
  renameTask: (taskId: string, name: string, projectId?: string) => Promise<void>
  removeProjectTasks: (projectId: string) => void
  refreshActiveTask: () => Promise<void>
  submitParameter: (parameter: string, value: unknown, unit?: string, displayValue?: string) => Promise<void>
  applyTaskState: (state: TaskStateDto) => void
}

function stateToSummary(state: TaskStateDto): TaskSummary {
  return {
    id: state.task_id,
    name: state.name,
    description: state.description,
    discipline: state.discipline,
    status: 'in_progress',
  }
}

function workflowToNav(workflow: TaskSummaryDto): TaskSummary {
  return toNavTaskSummary(workflow)
}

function withRenamedTaskName(tasks: TaskSummary[], taskId: string, name: string): TaskSummary[] {
  return tasks.map((task) => (task.id === taskId ? { ...task, name } : task))
}

async function ensureProjectForTask(projectId?: string): Promise<string | undefined> {
  const activeProjectId = getActiveSessionId()
  if (!projectId || projectId === activeProjectId) {
    return activeProjectId
  }
  await useProjectStore.getState().selectProject(projectId)
  return projectId
}

function collapseRightPanelForNoTask() {
  useRightPanelStore.getState().reset(false)
  useUiStore.setState({ rightCollapsed: true })
}

export const useTaskStore = create<TaskStoreState>((set, get) => ({
  sessionId: null,
  loading: false,
  userError: null,
  activeTask: null,
  activeTaskState: null,
  availableTasks: useMockData ? mockAvailableTasks : [],
  recentTasks: useMockData ? mockRecentTasks : [],
  projectTasks: {},

  loadWorkspace: async () => {
    if (useMockData) {
      return
    }

    const sessionId = getActiveSessionId()
    if (!sessionId) {
      set({ sessionId: null, loading: false, userError: null })
      await get().loadRecentTasksGlobal()
      try {
        const workflows = await taskApi.listWorkflows()
        const availableTasks = workflows
          .filter((workflow) => workflow.available)
          .map((workflow) => workflowToNav(workflowToSummary(workflow)))
        set({ availableTasks })
      } catch (error) {
        set({ userError: toUserFacingError(error) })
      }
      return
    }

    set({ loading: true, userError: null })
    try {
      const [workflows, taskList] = await Promise.all([
        taskApi.listWorkflows(),
        taskApi.list(sessionId),
      ])
      await get().loadRecentTasksGlobal()

      const availableTasks = workflows
        .filter((workflow) => workflow.available)
        .map((workflow) => workflowToNav(workflowToSummary(workflow)))

      let activeTask: TaskSummary | null = null
      let activeTaskState: TaskStateDto | null = null

      if (taskList.active_task_id) {
        activeTaskState = await taskApi.get(taskList.active_task_id, taskList.session_id)
        activeTask = stateToSummary(activeTaskState)
      }

      set((state) => ({
        sessionId: taskList.session_id,
        availableTasks,
        activeTask,
        activeTaskState,
        projectTasks: {
          ...state.projectTasks,
          [sessionId]: taskList.tasks.map((task) => toNavTaskSummary(task)),
        },
        loading: false,
        userError: null,
      }))
      useRightPanelStore.getState().syncForActiveTask(Boolean(activeTask))
    } catch (error) {
      set({
        loading: false,
        userError: toUserFacingError(error),
      })
    }
  },

  loadProjectTasks: async (projectId: string) => {
    if (useMockData) {
      if (projectId === 'proj_refinery') {
        set((state) => ({
          projectTasks: {
            ...state.projectTasks,
            [projectId]: mockRecentTasks.slice(0, 1),
          },
        }))
      }
      return
    }

    try {
      const taskList = await taskApi.list(projectId)
      set((state) => ({
        projectTasks: {
          ...state.projectTasks,
          [projectId]: taskList.tasks.map((task) => toNavTaskSummary(task)),
        },
      }))
    } catch (error) {
      set({ userError: toUserFacingError(error) })
    }
  },

  loadRecentTasksGlobal: async () => {
    if (useMockData) {
      set({ recentTasks: mockRecentTasks })
      return
    }

    try {
      const response = await taskApi.listRecentGlobal()
      set({
        recentTasks: response.recent_tasks.map((task) => toNavTaskSummary(task)),
      })
    } catch (error) {
      set({ userError: toUserFacingError(error) })
    }
  },

  selectTask: async (taskId: string, projectId?: string) => {
    if (useMockData) {
      const task =
        get().availableTasks.find((item) => item.id === taskId) ??
        get().recentTasks.find((item) => item.id === taskId) ??
        Object.values(get().projectTasks)
          .flat()
          .find((item) => item.id === taskId)
      if (task) {
        set({
          activeTask: {
            ...stateToSummary(mockTaskState),
            id: task.id,
            projectId: projectId ?? task.projectId,
          },
          activeTaskState: mockTaskState,
        })
        useRightPanelStore.getState().syncForActiveTask(true)
      }
      return
    }

    set({ loading: true, userError: null })
    try {
      const sessionId = await ensureProjectForTask(projectId)
      if (!sessionId) {
        set({
          loading: false,
          userError: {
            code: 'project_required',
            title: 'No project selected',
            whatHappened: 'Select or create a project before opening a task.',
            possibleReason: 'Tasks belong to a project.',
            nextAction: 'Create or select a project in the left panel.',
            retryable: false,
          },
        })
        return
      }

      const state = await taskApi.activate(taskId, sessionId)
      set({
        sessionId,
        activeTask: stateToSummary(state),
        activeTaskState: state,
        loading: false,
        userError: null,
      })
      await get().loadWorkspace()
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  createTask: async (workflowId: string) => {
    if (useMockData) {
      const task = get().availableTasks.find((item) => item.id === workflowId)
      if (task) {
        set({
          activeTask: stateToSummary(mockTaskState),
          activeTaskState: mockTaskState,
        })
        useRightPanelStore.getState().syncForActiveTask(true)
      }
      return
    }

    const sessionId = get().sessionId ?? getActiveSessionId()
    if (!sessionId) {
      set({
        userError: {
          code: 'project_required',
          title: 'No project selected',
          whatHappened: 'Create or select a project before starting a task.',
          possibleReason: 'Tasks must be created inside a project.',
          nextAction: 'Use Create new project in the left panel.',
          retryable: false,
        },
      })
      return
    }

    set({ loading: true, userError: null })
    try {
      const state = await taskApi.create(workflowId, sessionId)
      set({
        activeTask: stateToSummary(state),
        activeTaskState: state,
        loading: false,
        userError: null,
      })
      await get().loadWorkspace()
      await get().loadProjectTasks(sessionId)
      await useProjectStore.getState().loadProjects()
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  clearActiveTask: () => {
    collapseRightPanelForNoTask()
    set({ activeTask: null, activeTaskState: null })
  },

  removeProjectTasks: (projectId: string) => {
    set((state) => {
      const { [projectId]: _removed, ...projectTasks } = state.projectTasks
      return { projectTasks }
    })
  },

  deleteTask: async (taskId: string, projectId?: string) => {
    const { activeTask, recentTasks, projectTasks } = get()
    const projectTaskLists = Object.values(projectTasks).flat()
    const task =
      activeTask?.id === taskId
        ? activeTask
        : recentTasks.find((item) => item.id === taskId) ??
          projectTaskLists.find((item) => item.id === taskId) ??
          null

    if (!task) {
      return
    }

    if (!confirmTaskDeletion(task.name)) {
      return
    }

    const resolvedProjectId = projectId ?? task.projectId ?? get().sessionId ?? getActiveSessionId()

    if (useMockData) {
      if (activeTask?.id === taskId) {
        collapseRightPanelForNoTask()
      }
      set((state) => ({
        activeTask: state.activeTask?.id === taskId ? null : state.activeTask,
        activeTaskState: state.activeTask?.id === taskId ? null : state.activeTaskState,
        recentTasks: state.recentTasks.filter((item) => item.id !== taskId),
        projectTasks: Object.fromEntries(
          Object.entries(state.projectTasks).map(([id, tasks]) => [
            id,
            tasks.filter((item) => item.id !== taskId),
          ]),
        ),
      }))
      return
    }

    if (!resolvedProjectId) {
      return
    }

    set({ loading: true, userError: null })
    try {
      await taskApi.delete(taskId, resolvedProjectId)

      if (activeTask?.id === taskId) {
        collapseRightPanelForNoTask()
        set({ activeTask: null, activeTaskState: null })
      }

      await get().loadWorkspace()
      await get().loadProjectTasks(resolvedProjectId)
      await useProjectStore.getState().loadProjects()
      set({ loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  renameTask: async (taskId: string, name: string, projectId?: string) => {
    const trimmed = name.trim()
    if (!trimmed) {
      return
    }

    const resolvedProjectId = projectId ?? get().sessionId ?? getActiveSessionId()

    if (useMockData) {
      set((state) => ({
        activeTask:
          state.activeTask?.id === taskId ? { ...state.activeTask, name: trimmed } : state.activeTask,
        activeTaskState:
          state.activeTaskState?.task_id === taskId
            ? { ...state.activeTaskState, name: trimmed }
            : state.activeTaskState,
        recentTasks: withRenamedTaskName(state.recentTasks, taskId, trimmed),
        projectTasks: Object.fromEntries(
          Object.entries(state.projectTasks).map(([id, tasks]) => [
            id,
            withRenamedTaskName(tasks, taskId, trimmed),
          ]),
        ),
        userError: null,
      }))
      return
    }

    if (!resolvedProjectId) {
      return
    }

    set({ loading: true, userError: null })
    try {
      const state = await taskApi.rename(taskId, trimmed, resolvedProjectId)
      const summary = stateToSummary(state)
      set((current) => ({
        activeTask: current.activeTask?.id === taskId ? summary : current.activeTask,
        activeTaskState: current.activeTask?.id === taskId ? state : current.activeTaskState,
        recentTasks: withRenamedTaskName(current.recentTasks, taskId, trimmed),
        projectTasks: Object.fromEntries(
          Object.entries(current.projectTasks).map(([id, tasks]) => [
            id,
            withRenamedTaskName(tasks, taskId, trimmed),
          ]),
        ),
        loading: false,
        userError: null,
      }))
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  refreshActiveTask: async () => {
    const activeTask = get().activeTask
    if (!activeTask || useMockData) {
      return
    }
    try {
      const state = await taskApi.get(activeTask.id, get().sessionId ?? getActiveSessionId())
      set({ activeTask: stateToSummary(state), activeTaskState: state })
    } catch (error) {
      set({ userError: toUserFacingError(error) })
    }
  },

  submitParameter: async (parameter: string, value: unknown, unit?: string, displayValue?: string) => {
    const activeTask = get().activeTask
    if (!activeTask) {
      return
    }

    if (useMockData) {
      const state = get().activeTaskState
      if (!state) {
        return
      }

      const nextParameters = state.parameters.map((item) =>
        item.name === parameter
          ? { ...item, value, status: 'confirmed' as const }
          : item,
      )
      const resolvedDisplayValue = displayValue ?? formatEngineeringDisplayValue(value, unit)

      set({
        userError: null,
        activeTaskState: {
          ...state,
          parameters: nextParameters,
          inputs: {
            ...state.inputs,
            [parameter]: {
              input_id: parameter,
              value,
              unit: unit ?? 'dimensionless',
              display_value: resolvedDisplayValue,
            },
          },
          progress: {
            ...state.progress,
            missing_inputs: state.progress.missing_inputs.filter((item) => item !== parameter),
          },
        },
      })
      return
    }

    const snapshot = get().activeTaskState
    set({ userError: null })

    if (snapshot) {
      set({
        activeTaskState: applyOptimisticParameterSubmit(snapshot, parameter, value, unit, displayValue),
      })
    }

    try {
      const state = await inputApi.submit(
        activeTask.id,
        { parameter, value, unit },
        get().sessionId ?? getActiveSessionId(),
      )

      const previousDisplayOutputs = get().activeTaskState?.display_outputs ?? []
      const mergedDisplayOutputs = mergeDisplayOutputs(previousDisplayOutputs, state.display_outputs)

      set({
        activeTask: stateToSummary(state),
        activeTaskState: {
          ...state,
          display_outputs: mergedDisplayOutputs,
        },
        userError: null,
      })

      startTransition(() => {
        set({
          activeTask: stateToSummary(state),
          activeTaskState: {
            ...state,
            display_outputs: mergedDisplayOutputs,
          },
        })
      })
    } catch (error) {
      if (snapshot) {
        set({ activeTaskState: snapshot })
      }
      set({ userError: toUserFacingError(error) })
    }
  },

  applyTaskState: (state) => {
    set({
      activeTask: stateToSummary(state),
      activeTaskState: state,
      userError: null,
    })
  },
}))
