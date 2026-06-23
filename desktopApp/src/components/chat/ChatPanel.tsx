import { useEffect, useRef } from 'react'

import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { useChatStore } from '@/store/chatStore'
import { useTaskStore } from '@/store/taskStore'

import type { ChatContextDto } from '@/types/backend/chat'

import './ChatPanel.css'

interface ChatPanelProps {
  variant?: 'center' | 'sidebar'
  taskId?: string | null
  context?: ChatContextDto | null
}

function formatContext(context: ChatContextDto | null | undefined): string | null {
  if (!context?.task_id) {
    return null
  }

  const parts = [
    context.workflow_id ? `Workflow: ${context.workflow_id}` : null,
    context.current_step_id ? `Step: ${context.current_step_id}` : null,
    context.missing_inputs?.length ? `Missing: ${context.missing_inputs.join(', ')}` : null,
    context.output_count ? `Outputs: ${context.output_count}` : null,
  ].filter(Boolean)

  return parts.length > 0 ? parts.join(' · ') : `Task ${context.task_id}`
}

export function ChatPanel({ variant = 'center', taskId, context }: ChatPanelProps) {
  const messages = useChatStore((state) => state.messages)
  const loading = useChatStore((state) => state.loading)
  const userError = useChatStore((state) => state.userError)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const loadMessages = useChatStore((state) => state.loadMessages)
  const activeTask = useTaskStore((state) => state.activeTask)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    void loadMessages()
  }, [loadMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const resolvedTaskId = taskId ?? activeTask?.id ?? null
  const contextLine = formatContext(context)
  const isCenter = variant === 'center'

  return (
    <section className={`chat-panel chat-panel--${variant}`}>
      {isCenter ? (
        <header className="chat-panel__header">
          <h2 className="chat-panel__title">AI Workspace</h2>
          <p className="chat-panel__subtitle">
            Ask engineering questions, explore standards, or start a calculation workflow.
          </p>
        </header>
      ) : null}

      {contextLine ? <div className="chat-panel__context">{contextLine}</div> : null}
      {userError ? (
        <ErrorBanner
          error={userError}
          compact
          onRetry={() => {
            void loadMessages()
          }}
        />
      ) : null}

      <div className="chat-panel__messages" aria-live="polite">
        {messages.length === 0 ? (
          <p className="chat-panel__empty">Start a conversation with the engineering assistant.</p>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        disabled={loading}
        placeholder={
          resolvedTaskId
            ? 'Ask about this task, its inputs, or calculation outputs…'
            : 'Ask an engineering question or request a calculation…'
        }
        onSend={(message) => sendMessage(message, resolvedTaskId ?? undefined)}
      />
    </section>
  )
}
