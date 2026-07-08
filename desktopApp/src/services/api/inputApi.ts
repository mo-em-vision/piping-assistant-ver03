import { backendClient } from './backendClient'
import { requestManager } from './requestManager'
import { parseTaskState } from './responseParser'
import { tracedRequest } from '@/services/performance/tracedRequest'

import type { TaskStateDto } from '@/types/backend/api'
import type { ParameterEditImpactDto } from '@/types/backend/api'
import type { SubmitInputPayload } from '@/types/backend/parameters'

export const inputApi = {
  submit(taskId: string, payload: SubmitInputPayload, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`inputs:submit:${taskId}:${payload.parameter}`, () =>
      backendClient
        .post<TaskStateDto>(`/api/v1/tasks/${taskId}/inputs${query}`, payload)
        .then(parseTaskState),
    )
  },

  submitTraced(
    taskId: string,
    payload: SubmitInputPayload,
    traceId: string,
    sessionId?: string,
  ) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`inputs:submit:${taskId}:${payload.parameter}`, () =>
      tracedRequest<TaskStateDto>(
        `/api/v1/tasks/${taskId}/inputs${query}`,
        { method: 'POST', body: payload },
        { traceId, trigger: 'submit_input', taskId },
      ).then(parseTaskState),
    )
  },

  previewEdit(taskId: string, parameter: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`inputs:edit-preview:${taskId}:${parameter}`, () =>
      backendClient.get<ParameterEditImpactDto>(
        `/api/v1/tasks/${taskId}/inputs/${encodeURIComponent(parameter)}/edit-impact${query}`,
      ),
    )
  },

  beginEdit(taskId: string, parameter: string, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`inputs:edit:${taskId}:${parameter}`, () =>
      backendClient
        .post<TaskStateDto>(`/api/v1/tasks/${taskId}/inputs/${encodeURIComponent(parameter)}/edit${query}`, {})
        .then(parseTaskState),
    )
  },
}
