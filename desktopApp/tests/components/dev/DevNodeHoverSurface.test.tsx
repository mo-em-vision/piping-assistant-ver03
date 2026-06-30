import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DevNodeHoverProvider } from '@/components/dev/DevNodeHoverProvider'
import { DevNodeHoverSurface } from '@/components/dev/DevNodeHoverSurface'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useUiStore } from '@/store/uiStore'
import type { NodeProvenanceDto } from '@/types/backend/api'

vi.mock('@/config/env', () => ({
  env: { devMode: true },
}))

const mockProvenance: NodeProvenanceDto = {
  node_id: 'B313-304.1.1',
  title: 'Required Thickness',
  standard: 'ASME B31.3',
  paragraph: '304.1.1',
  hover_excerpt: 'The required thickness of straight sections of pipe shall be determined.',
  source_field: 'purpose',
}

describe('DevNodeHoverSurface (dev mode)', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(true)
    useUiStore.setState({ rightCollapsed: true })
  })

  it('shows compact node tooltip on hover', () => {
    render(
      <DevNodeHoverProvider>
        <DevNodeHoverSurface provenance={mockProvenance}>
          <p>Node text</p>
        </DevNodeHoverSurface>
      </DevNodeHoverProvider>,
    )

    fireEvent.mouseEnter(screen.getByText('Node text'), { clientX: 40, clientY: 60 })

    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    expect(screen.getByRole('tooltip')).toHaveTextContent('B313-304.1.1')
    expect(screen.getByRole('tooltip')).toHaveTextContent('purpose')
  })

  it('opens node edit tab when provenance text is clicked', () => {
    render(
      <DevNodeHoverProvider>
        <DevNodeHoverSurface provenance={mockProvenance}>
          <p>Node text</p>
        </DevNodeHoverSurface>
      </DevNodeHoverProvider>,
    )

    fireEvent.click(screen.getByText('Node text'))

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('edit-node-B313-304.1.1')
    expect(useUiStore.getState().rightCollapsed).toBe(false)
  })
})
