import { create } from 'zustand'

import { projectApi } from '@/services/api/projectApi'
import { projectToSummary } from '@/services/api/responseParser'
import { readActiveProjectId, writeActiveProjectId } from '@/services/storage/projectPreferences'
import { toUserFacingError } from '@/types/backend/errors'
import type { UserFacingError } from '@/types/frontend/userError'

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
}))

export function getActiveSessionId(): string | undefined {
  return useProjectStore.getState().activeProjectId ?? readActiveProjectId() ?? undefined
}
