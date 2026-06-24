import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NodeReferenceTab } from '@/components/standards/NodeReferenceTab'
import { standardsApi } from '@/services/api/standardsApi'

vi.mock('@/services/api/standardsApi', () => ({
  standardsApi: {
    getNode: vi.fn(),
  },
}))

const mockedGetNode = vi.mocked(standardsApi.getNode)

describe('NodeReferenceTab', () => {
  beforeEach(() => {
    mockedGetNode.mockReset()
  })

  it('renders only markdown body without duplicate metadata header', async () => {
    mockedGetNode.mockResolvedValue({
      node_id: 'B313-304.1.1',
      title: 'Required Thickness and Nomenclature for Straight Pipe',
      standard: 'ASME B31.3',
      paragraph: '304.1.1',
      section: '304 Pressure Design of Components',
      hover_excerpt:
        'The required thickness of straight sections of pipe shall be determined in accordance with eq. (2).',
      body: '# ASME B31.3 Paragraph 304.1.1\n\n## (a)\n\nBody-only paragraph content.',
    })

    render(<NodeReferenceTab nodeId="B313-304.1.1" />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'ASME B31.3 Paragraph 304.1.1' })).toBeInTheDocument()
    })

    expect(
      screen.queryByRole('heading', { name: 'Required Thickness and Nomenclature for Straight Pipe' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('ASME B31.3 · 304.1.1 · 304 Pressure Design of Components')).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        'The required thickness of straight sections of pipe shall be determined in accordance with eq. (2).',
      ),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Body-only paragraph content.')).toBeInTheDocument()
  })
})
