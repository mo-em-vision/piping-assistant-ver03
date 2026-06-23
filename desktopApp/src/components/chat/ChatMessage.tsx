import type { ChatMessageDto } from '@/types/backend/chat'

interface ChatMessageProps {
  message: ChatMessageDto
}

export function ChatMessage({ message }: ChatMessageProps) {
  const roleClass = message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'
  const label = message.role === 'user' ? 'You' : 'Assistant'

  return (
    <article className={`chat-message ${roleClass}`}>
      <div className="chat-message__meta">{label}</div>
      <div className="chat-message__bubble">{message.content}</div>
    </article>
  )
}
