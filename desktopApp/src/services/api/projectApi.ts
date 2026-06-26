import { backendClient } from './backendClient'
import { requestManager } from './requestManager'
import { parseProjects } from './responseParser'

import type { ProjectActivateResponse, ProjectDto } from '@/types/backend/api'

export const projectApi = {
  list() {
    return requestManager.run('projects:list', () =>
      backendClient.get<{ projects: ProjectDto[] }>('/api/v1/projects').then(parseProjects),
    )
  },

  get(projectId: string) {
    return requestManager.run(`projects:get:${projectId}`, () =>
      backendClient.get<ProjectDto>(`/api/v1/projects/${projectId}`),
    )
  },

  create(name: string) {
    return requestManager.run('projects:create', () =>
      backendClient.post<ProjectDto>('/api/v1/projects', { name }),
    )
  },

  activate(projectId: string) {
    return requestManager.run(`projects:activate:${projectId}`, () =>
      backendClient.post<ProjectActivateResponse>(`/api/v1/projects/${projectId}/activate`),
    )
  },

  delete(projectId: string) {
    return requestManager.run(`projects:delete:${projectId}`, () =>
      backendClient.delete<{ id: string; deleted: boolean }>(`/api/v1/projects/${projectId}`),
    )
  },

  rename(projectId: string, name: string) {
    return requestManager.run(`projects:rename:${projectId}`, () =>
      backendClient.patch<ProjectDto>(`/api/v1/projects/${projectId}`, { name }),
    )
  },
}
