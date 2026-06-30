import { ChatMarkdownContent } from '@/components/chat/ChatMarkdownContent'
import { DevNodeHoverSurface } from '@/components/dev/DevNodeHoverSurface'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import type { ChatMessageDto, ChatSource } from '@/types/backend/chat'

interface ChatMessageProps {
  message: ChatMessageDto
}

function sourceReferenceKind(source: ChatSource): 'node' | 'table' {
  if (source.kind === 'node') {
    return 'node'
  }
  return 'table'
}

function sourceReferenceId(source: ChatSource): string {
  if (source.kind === 'node') {
    return source.node_id ?? source.id
  }
  return source.table_id ?? source.id
}

export function ChatMessage({ message }: ChatMessageProps) {
  const roleClass = message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'
  const label = message.role === 'user' ? 'You' : 'Assistant'
  const sources = message.sources ?? []

  return (
    <article className={`chat-message ${roleClass}`}>
      <div className="chat-message__meta">{label}</div>
      <div className="chat-message__bubble">
        {message.role === 'assistant' ? (
          <ChatMarkdownContent content={message.content} />
        ) : (
          message.content
        )}
        {message.role === 'assistant' && sources.length > 0 ? (
          <div className="chat-message__sources" data-testid="chat-message-sources">
            <span className="chat-message__sources-label">Sources:</span>
            {sources.map((source) => (
              <DevNodeHoverSurface key={`${source.kind}:${source.id}`} provenance={source.provenance}>
                <StandardReferenceLink
                  referenceKind={sourceReferenceKind(source)}
                  referenceId={sourceReferenceId(source)}
                  label={source.label}
                  provenance={source.provenance}
                />
              </DevNodeHoverSurface>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  )
}
