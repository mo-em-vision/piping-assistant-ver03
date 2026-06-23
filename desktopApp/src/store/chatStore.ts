import { create } from 'zustand'

import { chatApi } from '@/services/api/chatApi'
import { mockAssistantReply, mockChatMessages } from '@/mock/chat.mock'
import { toUserFacingError } from '@/types/backend/errors'
import type { UserFacingError } from '@/types/frontend/userError'
import type { ChatContextDto, ChatMessageDto } from '@/types/backend/chat'
import type { TaskStateDto } from '@/types/backend/api'

import { getActiveSessionId } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface ChatStoreState {
  messages: ChatMessageDto[]
  loading: boolean
  userError: UserFacingError | null
  lastContext: ChatContextDto | null
  loadMessages: () => Promise<void>
  sendMessage: (message: string, taskId?: string) => Promise<void>
}

function stateToSummary(state: TaskStateDto) {
  return {
    id: state.task_id,
    name: state.name,
    description: state.description,
    discipline: state.discipline,
    status: 'in_progress' as const,
  }
}

export const useChatStore = create<ChatStoreState>((set, get) => ({
  messages: useMockData ? mockChatMessages : [],
  loading: false,
  userError: null,
  lastContext: null,

  loadMessages: async () => {
    if (useMockData) {
      set({ messages: mockChatMessages, userError: null })
      return
    }

    const sessionId = getActiveSessionId()
    set({ loading: true, userError: null })
    try {
      const response = await chatApi.list(sessionId)
      set({ messages: response.messages, loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  sendMessage: async (message: string, taskId?: string) => {
    const sessionId = getActiveSessionId()
    const activeTask = useTaskStore.getState().activeTask

    if (useMockData) {
      const userMessage: ChatMessageDto = {
        id: `mock-user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      }
      const assistantMessage: ChatMessageDto = {
        id: `mock-assistant-${Date.now()}`,
        role: 'assistant',
        content: mockAssistantReply(message, Boolean(taskId ?? activeTask)),
        timestamp: new Date().toISOString(),
        status: 'ready',
      }
      set({
        messages: [...get().messages, userMessage, assistantMessage],
        userError: null,
      })
      return
    }

    set({ loading: true, userError: null })
    try {
      const response = await chatApi.send({ message, task_id: taskId }, sessionId)
      set({
        messages: [...get().messages, response.user_message, response.assistant_message],
        lastContext: response.context,
        loading: false,
        userError: null,
      })

      if (response.task_state) {
        useTaskStore.setState({
          activeTask: stateToSummary(response.task_state),
          activeTaskState: response.task_state,
        })
        await useTaskStore.getState().loadWorkspace()
      }
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },
}))
