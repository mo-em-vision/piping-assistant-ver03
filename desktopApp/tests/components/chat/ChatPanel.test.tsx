import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { mockProjects } from '@/mock/workspace.mock'
import { mockTaskState } from '@/mock/taskState.mock'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

describe('ChatPanel', () => {
  const clearMessages = vi.fn().mockResolvedValue(undefined)

  beforeEach(() => {
    clearMessages.mockClear()
    useChatStore.setState({
      messages: [],
      loading: false,
      sending: false,
      userError: null,
      lastContext: null,
      loadMessages: vi.fn().mockResolvedValue(undefined),
      sendMessage: vi.fn().mockResolvedValue(undefined),
      clearMessages,
    })
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
      activeTaskState: mockTaskState,
    })
  })

  it('shows project and task labels in sidebar variant', () => {
    render(<ChatPanel variant="sidebar" taskId={mockTaskState.task_id} />)

    expect(screen.getByText('project:')).toBeInTheDocument()
    expect(screen.getByText(mockProjects[0]!.name)).toBeInTheDocument()
    expect(screen.getByText('Task:')).toBeInTheDocument()
    expect(screen.getByText(mockTaskState.name)).toBeInTheDocument()
    expect(screen.queryByText(/Workflow:/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Step:/i)).not.toBeInTheDocument()
  })

  it('shows AI Workspace header in center variant', () => {
    render(<ChatPanel variant="center" />)

    expect(screen.getByRole('heading', { name: 'AI Workspace' })).toBeInTheDocument()
    expect(screen.queryByText(mockTaskState.name)).not.toBeInTheDocument()
  })

  it('reloads task-scoped messages when the sidebar task changes', () => {
    const loadMessages = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({
      messages: [],
      loading: false,
      sending: false,
      userError: null,
      lastContext: null,
      loadMessages,
      sendMessage: vi.fn().mockResolvedValue(undefined),
      clearMessages: vi.fn().mockResolvedValue(undefined),
    })

    const { rerender } = render(
      <ChatPanel variant="sidebar" taskId={mockTaskState.task_id} />,
    )

    expect(loadMessages).toHaveBeenCalledWith(mockTaskState.task_id)

    rerender(<ChatPanel variant="sidebar" taskId="another-task-id" />)

    expect(loadMessages).toHaveBeenCalledWith('another-task-id')
  })

  it('disables clear chat when there are no messages', () => {
    render(<ChatPanel variant="sidebar" taskId={mockTaskState.task_id} />)

    expect(screen.getByRole('button', { name: 'Clear chat history' })).toBeDisabled()
  })

  it('shows pending reply while a message is sending', () => {
    useChatStore.setState({
      messages: [
        {
          id: 'pending-user-1',
          role: 'user',
          content: 'quality factor',
          timestamp: '2026-01-01T00:00:00.000Z',
        },
      ],
      sending: true,
    })

    render(<ChatPanel variant="sidebar" taskId={mockTaskState.task_id} />)

    expect(screen.queryByText('Start a conversation with the engineering assistant.')).not.toBeInTheDocument()
    expect(screen.getByText('quality factor')).toBeInTheDocument()
    expect(screen.getByTestId('chat-pending-reply')).toBeInTheDocument()
    expect(screen.getByText('Generating response…')).toBeInTheDocument()
  })

  it('clears task-scoped chat when the clear button is clicked', () => {
    useChatStore.setState({
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Hello',
          timestamp: '2026-01-01T00:00:00.000Z',
        },
      ],
    })

    render(<ChatPanel variant="sidebar" taskId={mockTaskState.task_id} />)

    const clearButton = screen.getByRole('button', { name: 'Clear chat history' })
    expect(clearButton).toBeEnabled()
    fireEvent.click(clearButton)
    expect(clearMessages).toHaveBeenCalledWith(mockTaskState.task_id)
  })
})
