import { backendClient } from './backendClient'
import { requestManager } from './requestManager'

import type { ChatListResponse, ChatSendResponse, SendChatPayload } from '@/types/backend/chat'

function buildChatQuery(sessionId?: string, taskId?: string): string {
  const params = new URLSearchParams()
  if (sessionId) {
    params.set('session_id', sessionId)
  }
  if (taskId) {
    params.set('task_id', taskId)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const chatApi = {
  list(sessionId?: string, taskId?: string) {
    const query = buildChatQuery(sessionId, taskId)
    const cacheKey = `chat:list:${sessionId ?? 'default'}:${taskId ?? 'all'}`
    return requestManager.run(cacheKey, () =>
      backendClient.get<ChatListResponse>(`/api/v1/chat/messages${query}`),
    )
  },

  send(payload: SendChatPayload, sessionId?: string) {
    const query = buildChatQuery(sessionId)
    return requestManager.run(`chat:send:${sessionId ?? 'default'}`, () =>
      backendClient.post<ChatSendResponse>(`/api/v1/chat/messages${query}`, payload, {
        timeoutMs: 60_000,
      }),
    )
  },

  clear(sessionId?: string, taskId?: string) {
    const query = buildChatQuery(sessionId, taskId)
    const cacheKey = `chat:clear:${sessionId ?? 'default'}:${taskId ?? 'all'}`
    return requestManager.run(cacheKey, () =>
      backendClient.delete<ChatListResponse>(`/api/v1/chat/messages${query}`),
    )
  },
}
