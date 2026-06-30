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

describe('DevNodeTooltip click-to-edit', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset(true)
    useUiStore.setState({ rightCollapsed: true })
  })

  it('shows node id and source field', () => {
    render(
      <DevNodeHoverProvider>
        <DevNodeHoverSurface provenance={mockProvenance}>
          <p>Node text</p>
        </DevNodeHoverSurface>
      </DevNodeHoverProvider>,
    )

    fireEvent.mouseEnter(screen.getByText('Node text'), { clientX: 40, clientY: 60 })

    expect(screen.getByRole('tooltip')).toHaveTextContent('B313-304.1.1')
    expect(screen.getByRole('tooltip')).toHaveTextContent('purpose')
    expect(screen.getByRole('tooltip')).toHaveTextContent('Click to edit node')
  })

  it('opens node edit tab when tooltip is clicked', () => {
    render(
      <DevNodeHoverProvider>
        <DevNodeHoverSurface provenance={mockProvenance}>
          <p>Node text</p>
        </DevNodeHoverSurface>
      </DevNodeHoverProvider>,
    )

    fireEvent.mouseEnter(screen.getByText('Node text'), { clientX: 40, clientY: 60 })
    fireEvent.click(screen.getByRole('tooltip'))

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('edit-node-B313-304.1.1')
    expect(state.tabs.some((tab) => tab.kind === 'node-edit' && tab.nodeId === 'B313-304.1.1')).toBe(
      true,
    )
    expect(useUiStore.getState().rightCollapsed).toBe(false)
  })
})
