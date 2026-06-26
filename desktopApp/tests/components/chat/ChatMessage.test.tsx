import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatMessage } from '@/components/chat/ChatMessage'
import { useRightPanelStore } from '@/store/rightPanelStore'
import type { ChatMessageDto } from '@/types/backend/chat'

vi.mock('@/store/taskStore', () => ({
  useTaskStore: (selector: (state: { activeTaskState: null }) => unknown) =>
    selector({ activeTaskState: null }),
}))

function buildMessage(overrides: Partial<ChatMessageDto>): ChatMessageDto {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: '',
    timestamp: '2026-01-01T00:00:00.000Z',
    ...overrides,
  }
}

describe('ChatMessage', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset()
    useRightPanelStore.getState().setActiveTab('chat')
  })

  it('renders assistant markdown with bold labels', () => {
    render(
      <ChatMessage
        message={buildMessage({
          content: '**Definition:** The quality factor (E) adjusts allowable strength.',
        })}
      />,
    )

    const strong = screen.getByText('Definition:')
    expect(strong.tagName).toBe('STRONG')
    expect(screen.queryByText('**Definition:**')).not.toBeInTheDocument()
  })

  it('renders user messages as plain text', () => {
    render(
      <ChatMessage
        message={buildMessage({
          role: 'user',
          content: '**Definition:** quality factor',
        })}
      />,
    )

    expect(screen.getByText('**Definition:** quality factor')).toBeInTheDocument()
    expect(screen.queryByRole('strong')).not.toBeInTheDocument()
  })

  it('renders multi-paragraph assistant markdown as separate paragraphs', () => {
    const { container } = render(
      <ChatMessage
        message={buildMessage({
          content: 'First paragraph.\n\nSecond paragraph.',
        })}
      />,
    )

    const paragraphs = container.querySelectorAll('.chat-markdown__p')
    expect(paragraphs.length).toBe(2)
    expect(paragraphs[0]).toHaveTextContent('First paragraph.')
    expect(paragraphs[1]).toHaveTextContent('Second paragraph.')
  })

  it('renders assistant source links when sources are provided', () => {
    render(
      <ChatMessage
        message={buildMessage({
          content: 'Y values are temperature-dependent.',
          sources: [
            {
              kind: 'table',
              id: 'asme_b31.3_table_304_1_1',
              label: 'Table 304.1.1 — Temperature Coefficient Y',
              table_id: 'asme_b31.3_table_304_1_1',
              node_id: 'B313-table-304-1-1',
            },
          ],
        })}
      />,
    )

    expect(screen.getByTestId('chat-message-sources')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Table 304.1.1 — Temperature Coefficient Y' }),
    ).toBeInTheDocument()
  })

  it('opens inline table links in the reference tab and keeps the link visible', () => {
    render(
      <ChatMessage
        message={buildMessage({
          content: 'See [Table A-1A](table:asme_b31.3_A-1A) for quality factors.',
        })}
      />,
    )

    const link = screen.getByRole('button', { name: 'Table A-1A' })
    fireEvent.click(link)

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('ref-table-asme_b31.3_A-1A')
    expect(state.tabs.some((tab) => tab.id === 'ref-table-asme_b31.3_A-1A')).toBe(true)
    expect(screen.getByRole('button', { name: 'Table A-1A' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Table A-1A' }))
    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-asme_b31.3_A-1A')
    expect(screen.getByRole('button', { name: 'Table A-1A' })).toBeInTheDocument()
  })

  it('keeps source footer links after opening the reference tab', () => {
    render(
      <ChatMessage
        message={buildMessage({
          content: 'Y values are temperature-dependent.',
          sources: [
            {
              kind: 'table',
              id: 'asme_b31.3_table_304_1_1',
              label: 'Table 304.1.1 — Temperature Coefficient Y',
              table_id: 'asme_b31.3_table_304_1_1',
            },
          ],
        })}
      />,
    )

    const sourceLink = screen.getByRole('button', {
      name: 'Table 304.1.1 — Temperature Coefficient Y',
    })
    fireEvent.click(sourceLink)

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-asme_b31.3_table_304_1_1')
    expect(
      screen.getByRole('button', { name: 'Table 304.1.1 — Temperature Coefficient Y' }),
    ).toBeInTheDocument()
  })
})
