import { create } from 'zustand'

import { projectApi } from '@/services/api/projectApi'
import { projectToSummary } from '@/services/api/responseParser'
import {
  clearActiveProjectId,
  readActiveProjectId,
  writeActiveProjectId,
} from '@/services/storage/projectPreferences'
import { useTaskStore } from '@/store/taskStore'
import { toUserFacingError } from '@/types/backend/errors'
import type { UserFacingError } from '@/types/frontend/userError'
import { confirmProjectDeletion } from '@/utils/confirmProjectDeletion'

import { mockProjects } from '@/mock/workspace.mock'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface ProjectStoreState {
  activeProjectId: string | null
  projects: ReturnType<typeof projectToSummary>[]
  loading: boolean
  userError: UserFacingError | null
  loadProjects: () => Promise<string | null>
  selectProject: (projectId: string) => Promise<void>
  createProject: (name: string) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  renameProject: (projectId: string, name: string) => Promise<void>
}

export const useProjectStore = create<ProjectStoreState>((set, get) => ({
  activeProjectId: useMockData ? mockProjects[0]?.id ?? null : readActiveProjectId(),
  projects: useMockData ? mockProjects : [],
  loading: false,
  userError: null,

  loadProjects: async () => {
    if (useMockData) {
      const stored = readActiveProjectId()
      const activeProjectId = stored ?? mockProjects[0]?.id ?? null
      set({ projects: mockProjects, activeProjectId, userError: null })
      return activeProjectId
    }

    set({ loading: true, userError: null })
    try {
      const projects = (await projectApi.list())
        .map(projectToSummary)
        .filter((project) => project.id !== 'default')
      const stored = readActiveProjectId()
      const activeProjectId =
        stored && projects.some((project) => project.id === stored)
          ? stored
          : projects[0]?.id ?? null

      if (activeProjectId) {
        writeActiveProjectId(activeProjectId)
      } else {
        clearActiveProjectId()
      }

      set({
        projects,
        activeProjectId,
        loading: false,
        userError: null,
      })
      return activeProjectId
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
      return get().activeProjectId
    }
  },

  selectProject: async (projectId: string) => {
    if (useMockData) {
      writeActiveProjectId(projectId)
      set({ activeProjectId: projectId, userError: null })
      return
    }

    set({ loading: true, userError: null })
    try {
      const response = await projectApi.activate(projectId)
      writeActiveProjectId(response.session_id)
      set({
        activeProjectId: response.session_id,
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  createProject: async (name: string) => {
    if (useMockData) {
      const project = {
        id: `mock-${Date.now()}`,
        name,
        taskCount: 0,
        updatedAt: new Date().toISOString().slice(0, 10),
      }
      writeActiveProjectId(project.id)
      set({
        projects: [project, ...get().projects],
        activeProjectId: project.id,
        userError: null,
      })
      return
    }

    set({ loading: true, userError: null })
    try {
      const created = await projectApi.create(name)
      const summary = projectToSummary(created)
      writeActiveProjectId(summary.id)
      set({
        projects: [summary, ...get().projects.filter((project) => project.id !== summary.id)],
        activeProjectId: summary.id,
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  deleteProject: async (projectId: string) => {
    const project = get().projects.find((item) => item.id === projectId)
    if (!project) {
      return
    }

    if (!confirmProjectDeletion(project.name)) {
      return
    }

    const wasActive = get().activeProjectId === projectId

    if (useMockData) {
      const remaining = get().projects.filter((item) => item.id !== projectId)
      const nextActiveId = wasActive ? (remaining[0]?.id ?? null) : get().activeProjectId
      if (nextActiveId) {
        writeActiveProjectId(nextActiveId)
      } else {
        clearActiveProjectId()
      }
      useTaskStore.getState().removeProjectTasks(projectId)
      if (wasActive) {
        useTaskStore.getState().clearActiveTask()
      }
      set({
        projects: remaining,
        activeProjectId: nextActiveId,
        userError: null,
      })
      await useTaskStore.getState().loadRecentTasksGlobal()
      if (nextActiveId) {
        await useTaskStore.getState().loadWorkspace()
      }
      return
    }

    set({ loading: true, userError: null })
    try {
      await projectApi.delete(projectId)
      useTaskStore.getState().removeProjectTasks(projectId)
      if (wasActive) {
        useTaskStore.getState().clearActiveTask()
      }
      const activeProjectId = await get().loadProjects()
      if (activeProjectId) {
        await get().selectProject(activeProjectId)
      }
      await useTaskStore.getState().loadWorkspace()
      await useTaskStore.getState().loadRecentTasksGlobal()
      set({ loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  renameProject: async (projectId: string, name: string) => {
    const trimmed = name.trim()
    if (!trimmed) {
      return
    }

    if (useMockData) {
      set({
        projects: get().projects.map((project) =>
          project.id === projectId ? { ...project, name: trimmed } : project,
        ),
        userError: null,
      })
      return
    }

    set({ loading: true, userError: null })
    try {
      const updated = await projectApi.rename(projectId, trimmed)
      const summary = projectToSummary(updated)
      set({
        projects: get().projects.map((project) =>
          project.id === projectId ? summary : project,
        ),
        loading: false,
        userError: null,
      })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },
}))

export function getActiveSessionId(): string | undefined {
  return useProjectStore.getState().activeProjectId ?? readActiveProjectId() ?? undefined
}
