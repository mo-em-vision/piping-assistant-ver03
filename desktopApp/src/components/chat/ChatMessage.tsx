import { ChatMarkdownContent } from '@/components/chat/ChatMarkdownContent'
import { InlineCitationList } from '@/components/standards/InlineCitationText'
import type { ChatMessageDto, ChatSource } from '@/types/backend/chat'
import type { ReferenceChipDto } from '@/types/backend/outputs'

interface ChatMessageProps {
  message: ChatMessageDto
}

function sourceToChip(source: ChatSource): ReferenceChipDto {
  const referenceId =
    source.kind === 'node'
      ? source.node_id ?? source.id
      : source.table_id ?? source.id

  return {
    ref_type: source.kind === 'table' ? 'table' : 'node',
    id: source.id,
    label: source.label,
    target:
      source.kind === 'table'
        ? { table_id: referenceId, node_id: referenceId }
        : { node_id: referenceId },
  }
}

export function ChatMessage({ message }: ChatMessageProps) {
  const roleClass = message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'
  const label = message.role === 'user' ? 'You' : 'Assistant'
  const sources = message.sources ?? []
  const sourceChips = sources.map(sourceToChip)

  return (
    <article className={`chat-message ${roleClass}`}>
      <div className="chat-message__meta">{label}</div>
      <div className="chat-message__bubble">
        {message.role === 'assistant' ? (
          <ChatMarkdownContent content={message.content} />
        ) : (
          message.content
        )}
        {message.role === 'assistant' && sourceChips.length > 0 ? (
          <p className="chat-message__sources" data-testid="chat-message-sources">
            <InlineCitationList prefix="Sources:" chips={sourceChips} />
          </p>
        ) : null}
      </div>
    </article>
  )
}
