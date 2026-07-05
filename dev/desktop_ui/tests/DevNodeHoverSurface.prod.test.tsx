import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DevNodeHoverProvider } from '@dev-ui/DevNodeHoverProvider'
import { DevNodeHoverSurface } from '@dev-ui/DevNodeHoverSurface'
import type { NodeProvenanceDto } from '@/types/backend/api'

vi.mock('@/config/env', () => ({
  env: { devToolsAvailable: false },
}))

vi.mock('@dev-ui/devUiActive', () => ({
  getDevUiActive: () => false,
  subscribeDevUiActive: () => () => {},
}))

const mockProvenance: NodeProvenanceDto = {
  node_id: 'B313-304.1.1',
  hover_excerpt: 'Excerpt text',
}

describe('DevNodeHoverSurface (production mode)', () => {
  it('does not show tooltip when devMode is false', () => {
    render(
      <DevNodeHoverProvider>
        <DevNodeHoverSurface provenance={mockProvenance}>
          <p>Node text</p>
        </DevNodeHoverSurface>
      </DevNodeHoverProvider>,
    )

    fireEvent.mouseEnter(screen.getByText('Node text'))
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })
})
