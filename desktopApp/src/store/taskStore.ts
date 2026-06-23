import { create } from 'zustand'

import { inputApi } from '@/services/api/inputApi'
import { taskApi } from '@/services/api/taskApi'
import { toNavTaskSummary, workflowToSummary } from '@/services/api/responseParser'
import { getActiveSessionId } from '@/store/projectStore'
import { toUserFacingError } from '@/types/backend/errors'
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
  loadWorkspace: () => Promise<void>
  selectTask: (taskId: string) => Promise<void>
  createTask: (workflowId: string) => Promise<void>
  clearActiveTask: () => void
  refreshActiveTask: () => Promise<void>
  submitParameter: (parameter: string, value: unknown, unit?: string) => Promise<void>
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

export const useTaskStore = create<TaskStoreState>((set, get) => ({
  sessionId: null,
  loading: false,
  userError: null,
  activeTask: null,
  activeTaskState: null,
  availableTasks: useMockData ? mockAvailableTasks : [],
  recentTasks: useMockData ? mockRecentTasks : [],

  loadWorkspace: async () => {
    if (useMockData) {
      return
    }

    const sessionId = getActiveSessionId()
    set({ loading: true, userError: null })
    try {
      const [workflows, taskList] = await Promise.all([
        taskApi.listWorkflows(),
        taskApi.list(sessionId),
      ])

      const availableTasks = workflows
        .filter((workflow) => workflow.available)
        .map((workflow) => workflowToNav(workflowToSummary(workflow)))

      const recentTasks = taskList.recent_tasks.map((task) => toNavTaskSummary(task))

      let activeTask: TaskSummary | null = null
      let activeTaskState: TaskStateDto | null = null

      if (taskList.active_task_id) {
        activeTaskState = await taskApi.get(taskList.active_task_id, taskList.session_id)
        activeTask = stateToSummary(activeTaskState)
      }

      set({
        sessionId: taskList.session_id,
        availableTasks,
        recentTasks,
        activeTask,
        activeTaskState,
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({
        loading: false,
        userError: toUserFacingError(error),
      })
    }
  },

  selectTask: async (taskId: string) => {
    if (useMockData) {
      const task =
        get().availableTasks.find((item) => item.id === taskId) ??
        get().recentTasks.find((item) => item.id === taskId)
      if (task) {
        set({
          activeTask: { ...task, status: 'in_progress' },
          activeTaskState: mockTaskState,
        })
      }
      return
    }

    set({ loading: true, userError: null })
    try {
      const sessionId = get().sessionId ?? getActiveSessionId()
      const state = await taskApi.activate(taskId, sessionId)
      set({
        activeTask: stateToSummary(state),
        activeTaskState: state,
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  createTask: async (workflowId: string) => {
    if (useMockData) {
      const task = get().availableTasks.find((item) => item.id === workflowId)
      if (task) {
        set({
          activeTask: { ...task, status: 'in_progress' },
          activeTaskState: mockTaskState,
        })
      }
      return
    }

    set({ loading: true, userError: null })
    try {
      const sessionId = get().sessionId ?? getActiveSessionId()
      const state = await taskApi.create(workflowId, sessionId)
      set({
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

  clearActiveTask: () => set({ activeTask: null, activeTaskState: null }),

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

  submitParameter: async (parameter: string, value: unknown, unit?: string) => {
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
      const displayValue =
        typeof value === 'boolean'
          ? value
            ? 'Yes'
            : 'No'
          : unit && unit !== 'dimensionless'
            ? `${value} ${unit}`
            : String(value)

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
              display_value: displayValue,
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

    set({ loading: true, userError: null })
    try {
      const state = await inputApi.submit(
        activeTask.id,
        { parameter, value, unit },
        get().sessionId ?? getActiveSessionId(),
      )
      set({
        activeTask: stateToSummary(state),
        activeTaskState: state,
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },
}))
