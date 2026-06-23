import { backendClient } from './backendClient'
import { requestManager } from './requestManager'
import { parseTaskState } from './responseParser'

import type { TaskStateDto } from '@/types/backend/api'
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
}
