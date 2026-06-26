import { useEffect, useMemo, useRef } from 'react'

import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { ChatPendingReply } from './ChatPendingReply'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

import './ChatPanel.css'

interface ChatPanelProps {
  variant?: 'center' | 'sidebar'
  taskId?: string | null
}

export function ChatPanel({ variant = 'center', taskId }: ChatPanelProps) {
  const messages = useChatStore((state) => state.messages)
  const loading = useChatStore((state) => state.loading)
  const sending = useChatStore((state) => state.sending)
  const userError = useChatStore((state) => state.userError)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const clearMessages = useChatStore((state) => state.clearMessages)
  const activeTask = useTaskStore((state) => state.activeTask)
  const sessionId = useTaskStore((state) => state.sessionId)
  const projects = useProjectStore((state) => state.projects)
  const activeProjectId = useProjectStore((state) => state.activeProjectId)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const resolvedTaskId = taskId ?? activeTask?.id ?? null
  const isCenter = variant === 'center'
  const isSidebar = variant === 'sidebar'

  useEffect(() => {
    if (isSidebar && resolvedTaskId) {
      const hasMessagesForTask = messages.some(
        (message) => message.task_id === resolvedTaskId || message.task_id == null,
      )
      if (hasMessagesForTask && !loading) {
        return
      }
    }
    void loadMessages(isSidebar ? resolvedTaskId ?? undefined : undefined)
  }, [loadMessages, isSidebar, resolvedTaskId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const canClearChat = messages.length > 0 && !loading && !sending
  const isBusy = loading || sending

  const projectName = useMemo(() => {
    const projectId = sessionId ?? activeTask?.projectId ?? activeProjectId
    return projects.find((project) => project.id === projectId)?.name ?? activeTask?.projectName
  }, [sessionId, activeTask?.projectId, activeTask?.projectName, activeProjectId, projects])

  const taskName = activeTask?.name

  const clearChatButton = (
    <button
      type="button"
      className="chat-panel__clear-button"
      aria-label="Clear chat history"
      disabled={!canClearChat}
      onClick={() => {
        void clearMessages(isSidebar ? resolvedTaskId ?? undefined : undefined)
      }}
    >
      Clear chat
    </button>
  )

  return (
    <section className={`chat-panel chat-panel--${variant}`}>
      {isCenter ? (
        <header className="chat-panel__header">
          <div className="chat-panel__header-meta">
            <h2 className="chat-panel__title">AI Workspace</h2>
            <p className="chat-panel__subtitle">
              Ask engineering questions, explore standards, or start a calculation workflow.
            </p>
          </div>
          {clearChatButton}
        </header>
      ) : null}

      {isSidebar && taskName ? (
        <header className="chat-panel__task-header">
          <div className="chat-panel__task-header-meta">
            {projectName ? (
              <p className="chat-panel__context-line">
                <span className="chat-panel__context-label">project:</span>{' '}
                <span className="chat-panel__context-value">{projectName}</span>
              </p>
            ) : null}
            <h2 className="chat-panel__context-line chat-panel__context-line--task">
              <span className="chat-panel__context-label">Task:</span>{' '}
              <span className="chat-panel__context-value">{taskName}</span>
            </h2>
          </div>
          {clearChatButton}
        </header>
      ) : null}

      {userError ? (
        <ErrorBanner
          error={userError}
          compact
          onRetry={() => {
            void loadMessages(isSidebar ? resolvedTaskId ?? undefined : undefined)
          }}
        />
      ) : null}

      <div className="chat-panel__messages" aria-live="polite">
        {messages.length === 0 && !sending ? (
          <p className="chat-panel__empty">Start a conversation with the engineering assistant.</p>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}
        {sending ? <ChatPendingReply /> : null}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-panel__composer">
        <ChatInput
          disabled={isBusy}
          placeholder={
            resolvedTaskId
              ? 'Ask about this task, its inputs, or calculation outputs…'
              : 'Ask an engineering question or request a calculation…'
          }
          onSend={(message) => sendMessage(message, resolvedTaskId ?? undefined)}
        />
      </div>
    </section>
  )
}
