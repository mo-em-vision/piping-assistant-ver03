import './ChatPendingReply.css'

export function ChatPendingReply() {
  return (
    <article
      className="chat-message chat-message--assistant chat-message--pending"
      aria-busy="true"
      aria-label="Waiting for assistant response"
      data-testid="chat-pending-reply"
    >
      <div className="chat-message__meta">Assistant</div>
      <div className="chat-message__bubble">
        <span className="chat-message__pending-text">Generating response…</span>
      </div>
    </article>
  )
}
