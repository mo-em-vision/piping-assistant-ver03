import { useState } from 'react'

import { ComposerInlineInput } from '@/components/workflow/ComposerInlineInput'

interface ChatInputProps {
  disabled?: boolean
  placeholder?: string
  onSend: (message: string) => Promise<void> | void
}

export function ChatInput({ disabled, placeholder = '', onSend }: ChatInputProps) {
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
    <ComposerInlineInput
      value={value}
      onChange={setValue}
      placeholder={placeholder}
      disabled={disabled}
      submitting={submitting}
      canSubmit={Boolean(value.trim())}
      onSubmit={() => void handleSubmit()}
      variant="text"
      layout="fluid"
      autoFocus={false}
    />
  )
}
