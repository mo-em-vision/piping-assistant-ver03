import { create } from 'zustand'

import { chatApi } from '@/services/api/chatApi'
import { mockAssistantReply, mockChatMessages, mockSelectionExplanation } from '@/mock/chat.mock'
import { buildAskAiSelectionPrompt } from '@/templates/askAiSelectionPrompt'
import { toUserFacingError } from '@/types/backend/errors'
import type { UserFacingError } from '@/types/frontend/userError'
import type { ChatContextDto, ChatMessageDto } from '@/types/backend/chat'

import { getActiveSessionId, useProjectStore } from '@/store/projectStore'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface SendMessageOptions {
  displayMessage?: string
  mode?: 'workflow' | 'selection_explain' | 'task_assist'
}

interface ChatStoreState {
  messages: ChatMessageDto[]
  loading: boolean
  sending: boolean
  userError: UserFacingError | null
  lastContext: ChatContextDto | null
  loadMessages: (taskId?: string) => Promise<void>
  sendMessage: (message: string, taskId?: string, options?: SendMessageOptions) => Promise<void>
  clearMessages: (taskId?: string) => Promise<void>
  askAboutSelection: (selectedText: string) => Promise<void>
}

function resolveProjectName(sessionId: string | null, projectId?: string): string | undefined {
  const { projects, activeProjectId } = useProjectStore.getState()
  const resolvedProjectId = sessionId ?? projectId ?? activeProjectId
  return projects.find((project) => project.id === resolvedProjectId)?.name
}

export const useChatStore = create<ChatStoreState>((set, get) => ({
  messages: useMockData ? mockChatMessages : [],
  loading: false,
  sending: false,
  userError: null,
  lastContext: null,

  loadMessages: async (taskId?: string) => {
    if (useMockData) {
      set({ messages: mockChatMessages, userError: null })
      return
    }

    const sessionId = getActiveSessionId()
    set({ loading: true, userError: null })
    try {
      const response = await chatApi.list(sessionId, taskId)
      if (get().sending) {
        set({ loading: false, userError: null })
        return
      }
      set({ messages: response.messages, loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  sendMessage: async (message: string, taskId?: string, options?: SendMessageOptions) => {
    const sessionId = getActiveSessionId()
    const activeTask = useTaskStore.getState().activeTask
    const displayMessage = options?.displayMessage?.trim()
    const visibleUserContent = displayMessage || message

    if (useMockData) {
      const userMessage: ChatMessageDto = {
        id: `mock-user-${Date.now()}`,
        role: 'user',
        content: visibleUserContent,
        timestamp: new Date().toISOString(),
      }
      set({ sending: true, userError: null, messages: [...get().messages, userMessage] })
      const assistantMessage: ChatMessageDto = {
        id: `mock-assistant-${Date.now()}`,
        role: 'assistant',
        content:
          options?.mode === 'selection_explain'
            ? mockSelectionExplanation(visibleUserContent, message)
            : mockAssistantReply(message, Boolean(taskId ?? activeTask)),
        timestamp: new Date().toISOString(),
        status: options?.mode === 'selection_explain' ? 'explained' : 'ready',
      }
      set({
        messages: [...get().messages, assistantMessage],
        sending: false,
        userError: null,
      })
      return
    }

    if (get().sending) {
      return
    }

    const pendingUserId = `pending-user-${Date.now()}`
    const optimisticUserMessage: ChatMessageDto = {
      id: pendingUserId,
      role: 'user',
      content: visibleUserContent,
      timestamp: new Date().toISOString(),
      status: 'pending',
      task_id: taskId ?? null,
    }

    set({
      sending: true,
      userError: null,
      messages: [...get().messages, optimisticUserMessage],
    })
    try {
      const resolvedMode =
        options?.mode ?? (taskId ? 'task_assist' : undefined)
      const payload = {
        message,
        task_id: taskId,
        ...(displayMessage ? { display_message: displayMessage } : {}),
        ...(resolvedMode ? { mode: resolvedMode } : {}),
      }
      const response = await chatApi.send(payload, sessionId)
      const withoutPending = get().messages.filter((message) => !message.id.startsWith('pending-'))
      set({
        messages: [...withoutPending, response.user_message, response.assistant_message],
        lastContext: response.context,
        sending: false,
        userError: null,
      })

      const skipTaskRefresh =
        resolvedMode === 'selection_explain' || resolvedMode === 'task_assist'
      if (response.task_state && !skipTaskRefresh) {
        useTaskStore.getState().applyTaskState(response.task_state)
        await useTaskStore.getState().loadWorkspace()
      }
    } catch (error) {
      set({
        messages: get().messages.filter((message) => message.id !== pendingUserId),
        sending: false,
        userError: toUserFacingError(error),
      })
    }
  },

  clearMessages: async (taskId?: string) => {
    if (useMockData) {
      set({ messages: [], lastContext: null, userError: null })
      return
    }

    if (get().loading) {
      return
    }

    const sessionId = getActiveSessionId()
    set({ loading: true, userError: null })
    try {
      await chatApi.clear(sessionId, taskId)
      set({ messages: [], lastContext: null, loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  askAboutSelection: async (selectedText: string) => {
    const trimmedSelection = selectedText.trim()
    if (!trimmedSelection) {
      return
    }

    const activeTask = useTaskStore.getState().activeTask
    const activeTaskState = useTaskStore.getState().activeTaskState
    const sessionId = useTaskStore.getState().sessionId
    if (!activeTask) {
      return
    }

    const projectName = resolveProjectName(sessionId, activeTask.projectId) ?? activeTask.projectName

    const prompt = buildAskAiSelectionPrompt({
      selectedText: trimmedSelection,
      taskState: activeTaskState,
      taskName: activeTask.name,
      taskId: activeTask.id,
      workflowId: activeTaskState?.workflow_id,
      currentStepId: activeTaskState?.progress.current_step_id,
      discipline: activeTask.discipline,
      activeNodeHeading: activeTaskState?.active_node_context?.display_heading,
      projectName,
    })

    useUiStore.setState({ rightCollapsed: false })
    useRightPanelStore.getState().setActiveTab('chat')
    await get().sendMessage(prompt, activeTask.id, {
      displayMessage: trimmedSelection,
      mode: 'selection_explain',
    })
  },
}))
