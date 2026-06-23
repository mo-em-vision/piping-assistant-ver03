import { useState } from 'react'

interface ChatInputProps {
  disabled?: boolean
  placeholder?: string
  onSend: (message: string) => Promise<void> | void
}

export function ChatInput({ disabled, placeholder, onSend }: ChatInputProps) {
  const [value, setValue] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    const text = value.trim()
    if (!text || disabled || submitting) {
      return
    }

    setSubmitting(true)
    try {
      await onSend(text)
      setValue('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      className="chat-input"
      onSubmit={(event) => {
        event.preventDefault()
        void handleSubmit()
      }}
    >
      <textarea
        className="chat-input__field"
        value={value}
        placeholder={placeholder}
        disabled={disabled || submitting}
        rows={2}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void handleSubmit()
          }
        }}
      />
      <button type="submit" className="chat-input__submit" disabled={disabled || submitting || !value.trim()}>
        {submitting ? 'Sending…' : 'Send'}
      </button>
    </form>
  )
}
