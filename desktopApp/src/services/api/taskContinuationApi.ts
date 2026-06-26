import { backendClient } from './backendClient'
import { requestManager } from './requestManager'

import type { TaskContinuationSuggestionsDto } from '@/types/backend/continuation'

function withSession(path: string, sessionId?: string) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return `${path}${query}`
}

export const taskContinuationApi = {
  getSuggestions(taskId: string, sessionId?: string) {
    return requestManager.run(`continuation:${taskId}`, () =>
      backendClient.get<TaskContinuationSuggestionsDto>(
        withSession(`/api/v1/tasks/${taskId}/continuation-suggestions`, sessionId),
      ),
    )
  },
}
