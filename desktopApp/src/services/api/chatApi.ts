import { backendClient } from './backendClient'
import { requestManager } from './requestManager'

import type { ChatListResponse, ChatSendResponse, SendChatPayload } from '@/types/backend/chat'

export const chatApi = {
  list(sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`chat:list:${sessionId ?? 'default'}`, () =>
      backendClient.get<ChatListResponse>(`/api/v1/chat/messages${query}`),
    )
  },

  send(payload: SendChatPayload, sessionId?: string) {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    return requestManager.run(`chat:send:${sessionId ?? 'default'}`, () =>
      backendClient.post<ChatSendResponse>(`/api/v1/chat/messages${query}`, payload, {
        timeoutMs: 60_000,
      }),
    )
  },
}
