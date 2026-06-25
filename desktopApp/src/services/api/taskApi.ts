import { backendClient } from './backendClient'
import { requestManager } from './requestManager'
import { parseTaskList, parseTaskState, parseWorkflows } from './responseParser'

import type { RecentTasksResponse, TaskListResponse, TaskStateDto, WorkflowDto } from '@/types/backend/api'

export const taskApi = {
  list(sessionId: string) {
    const query = `?session_id=${encodeURIComponent(sessionId)}`
    return requestManager.run(`tasks:list:${sessionId}`, () =>
      backendClient.get<TaskListResponse>(`/api/v1/tasks${query}`).then(parseTaskList),
    )
  },

  get(taskId: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`tasks:get:${taskId}`, () =>
      backendClient.get<TaskStateDto>(`/api/v1/tasks/${taskId}${query}`).then(parseTaskState),
    )
  },

  create(workflowId: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`tasks:create:${workflowId}`, () =>
      backendClient.post<TaskStateDto>(`/api/v1/tasks${query}`, { workflow_id: workflowId }).then(parseTaskState),
    )
  },

  activate(taskId: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`tasks:activate:${taskId}`, () =>
      backendClient.post<TaskStateDto>(`/api/v1/tasks/${taskId}/activate${query}`).then(parseTaskState),
    )
  },

  delete(taskId: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`tasks:delete:${taskId}`, () =>
      backendClient.delete<{ task_id: string; deleted: boolean; session_id: string }>(
        `/api/v1/tasks/${taskId}${query}`,
      ),
    )
  },

  listWorkflows() {
    return requestManager.run('workflows:list', () =>
      backendClient.get<{ workflows: WorkflowDto[] }>('/api/v1/workflows').then(parseWorkflows),
    )
  },

  listRecentGlobal() {
    return requestManager.run('tasks:recent-global', () =>
      backendClient.get<RecentTasksResponse>('/api/v1/recent-tasks'),
    )
  },
}
