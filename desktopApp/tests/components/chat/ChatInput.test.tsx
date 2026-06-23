import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ChatInput } from '@/components/chat/ChatInput'

describe('ChatInput', () => {
  it('submits trimmed message on button click', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} placeholder="Ask a question" />)

    await user.type(screen.getByPlaceholderText('Ask a question'), '  What is ASME B31.3?  ')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('What is ASME B31.3?')
  })

  it('disables send when message is empty', () => {
    render(<ChatInput onSend={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('clears the field after a successful send', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} />)

    const field = screen.getByRole('textbox')
    await user.type(field, 'Hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(field).toHaveValue('')
  })
})
