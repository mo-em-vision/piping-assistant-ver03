import { beforeEach, describe, expect, it, vi } from 'vitest'

import { mockProjects } from '@/mock/workspace.mock'
import { mockTaskState } from '@/mock/taskState.mock'
import { chatApi } from '@/services/api/chatApi'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore } from '@/store/projectStore'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'

vi.mock('@/services/api/chatApi', () => ({
  chatApi: {
    list: vi.fn(),
    send: vi.fn(),
    clear: vi.fn(),
  },
}))

const mockedSend = vi.mocked(chatApi.send)
const mockedClear = vi.mocked(chatApi.clear)

describe('chatStore sendMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0]?.id ?? null,
    })
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      sessionId: mockProjects[0]?.id ?? null,
      loadWorkspace: vi.fn().mockResolvedValue(undefined),
    })
    useChatStore.setState({
      messages: [],
      loading: false,
      sending: false,
      userError: null,
      lastContext: null,
    })
    mockedSend.mockResolvedValue({
      session_id: 'session-1',
      user_message: {
        id: 'user-1',
        role: 'user',
        content: 'What is E?',
        timestamp: '2026-01-01T00:00:00.000Z',
      },
      assistant_message: {
        id: 'assistant-1',
        role: 'assistant',
        content: 'E is the weld joint efficiency factor.',
        timestamp: '2026-01-01T00:00:01.000Z',
      },
      response: { status: 'assisted' },
      context: {},
      task_state: null,
    })
  })

  it('uses task_assist mode for task-scoped chat and does not refresh workspace', async () => {
    await useChatStore.getState().sendMessage('What is E?', mockTaskState.task_id)

    expect(mockedSend).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'What is E?',
        task_id: mockTaskState.task_id,
        mode: 'task_assist',
      }),
      mockProjects[0]?.id ?? null,
    )
    expect(useTaskStore.getState().loadWorkspace).not.toHaveBeenCalled()
  })

  it('shows an optimistic user message while waiting for the assistant reply', async () => {
    let resolveSend: ((value: Awaited<ReturnType<typeof mockedSend>>) => void) | undefined
    mockedSend.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSend = resolve
        }),
    )

    const sendPromise = useChatStore.getState().sendMessage('What is E?', mockTaskState.task_id)

    expect(useChatStore.getState().sending).toBe(true)
    expect(useChatStore.getState().messages).toEqual([
      expect.objectContaining({
        role: 'user',
        content: 'What is E?',
        status: 'pending',
      }),
    ])

    resolveSend?.({
      session_id: 'session-1',
      user_message: {
        id: 'user-1',
        role: 'user',
        content: 'What is E?',
        timestamp: '2026-01-01T00:00:00.000Z',
      },
      assistant_message: {
        id: 'assistant-1',
        role: 'assistant',
        content: 'E is the weld joint efficiency factor.',
        timestamp: '2026-01-01T00:00:01.000Z',
      },
      response: { status: 'assisted' },
      context: {},
      task_state: null,
    })

    await sendPromise

    expect(useChatStore.getState().sending).toBe(false)
    expect(useChatStore.getState().messages).toHaveLength(2)
    expect(useChatStore.getState().messages[0]?.id).toBe('user-1')
    expect(useChatStore.getState().messages[1]?.role).toBe('assistant')
  })
})

describe('chatStore askAboutSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useRightPanelStore.getState().reset()
    useUiStore.setState({ rightCollapsed: true })
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0]?.id ?? null,
    })
    useTaskStore.setState({
      activeTask: {
        id: mockTaskState.task_id,
        name: mockTaskState.name,
        description: mockTaskState.description,
        discipline: mockTaskState.discipline,
        status: 'in_progress',
      },
      activeTaskState: mockTaskState,
      sessionId: mockProjects[0]?.id ?? null,
    })
    useChatStore.setState({
      messages: [],
      loading: false,
      sending: false,
      userError: null,
      lastContext: null,
    })
    mockedSend.mockResolvedValue({
      session_id: 'session-1',
      user_message: {
        id: 'user-1',
        role: 'user',
        content: 'selected snippet',
        timestamp: '2026-01-01T00:00:00.000Z',
      },
      assistant_message: {
        id: 'assistant-1',
        role: 'assistant',
        content: 'Assistant reply',
        timestamp: '2026-01-01T00:00:01.000Z',
      },
      response: { status: 'ready' },
      context: {},
      task_state: null,
    })
  })

  it('switches to chat tab, expands right panel, and sends clarification prompt', async () => {
    await useChatStore.getState().askAboutSelection('selected snippet')

    expect(useUiStore.getState().rightCollapsed).toBe(false)
    expect(useRightPanelStore.getState().activeTabId).toBe('chat')
    const sendPayload = mockedSend.mock.calls[0]?.[0]
    expect(sendPayload).toMatchObject({
      display_message: 'selected snippet',
      task_id: mockTaskState.task_id,
      mode: 'selection_explain',
    })
    expect(sendPayload?.message).toContain('clarification')
    expect(sendPayload?.message).toContain('selected snippet')
    expect(sendPayload?.message).toContain('Pipe Thickness Calculation')
    expect(sendPayload?.message).toContain('## Current task state')
  })
})

describe('chatStore clearMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({
      projects: mockProjects,
      activeProjectId: mockProjects[0]?.id ?? null,
    })
    useTaskStore.setState({
      sessionId: mockProjects[0]?.id ?? null,
    })
    mockedClear.mockResolvedValue({
      session_id: mockProjects[0]?.id ?? 'session-1',
      messages: [],
    })
  })

  it('calls chatApi.clear and resets local chat state', async () => {
    useChatStore.setState({
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Hello',
          timestamp: '2026-01-01T00:00:00.000Z',
        },
      ],
      loading: false,
      sending: false,
      userError: null,
      lastContext: { task_id: mockTaskState.task_id },
    })

    await useChatStore.getState().clearMessages(mockTaskState.task_id)

    expect(mockedClear).toHaveBeenCalledWith(
      mockProjects[0]?.id ?? null,
      mockTaskState.task_id,
    )
    expect(useChatStore.getState().messages).toEqual([])
    expect(useChatStore.getState().lastContext).toBeNull()
    expect(useChatStore.getState().userError).toBeNull()
  })
})
