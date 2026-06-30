import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DevNodeHoverProvider } from '@/components/dev/DevNodeHoverProvider'
import { TextOutput } from '@/components/outputs/TextOutput'
import type { TextOutputBlock } from '@/types/backend/outputs'

vi.mock('@/config/env', () => ({
  env: { devMode: true },
}))

const block: TextOutputBlock = {
  id: 'text-1',
  type: 'text',
  content: 'Minimum required wall thickness applies.',
  provenance: {
    node_id: 'B313-304.1.2',
    title: 'Straight Pipe Under Internal Pressure',
    standard: 'ASME B31.3',
    paragraph: '304.1.2',
    hover_excerpt:
      'The minimum required wall thickness for straight pipe under internal pressure shall be computed.',
  },
}

describe('TextOutput dev hover', () => {
  it('shows node provenance tooltip for output text in dev mode', () => {
    render(
      <DevNodeHoverProvider>
        <TextOutput block={block} />
      </DevNodeHoverProvider>,
    )

    fireEvent.mouseEnter(screen.getByText(/Minimum required wall thickness applies/i), {
      clientX: 20,
      clientY: 30,
    })

    expect(screen.getByRole('tooltip')).toHaveTextContent('B313-304.1.2')
  })
})
