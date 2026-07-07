import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OutputRenderer } from '@/components/outputs/OutputRenderer'
import { TextOutput } from '@/components/outputs/TextOutput'
import { mockTaskState } from '@/mock/taskState.mock'

describe('TextOutput', () => {
  it('renders title and content', () => {
    const block = mockTaskState.display_outputs.find((item) => item.type === 'text')
    if (!block || block.type !== 'text') {
      throw new Error('Expected text block in mock task state')
    }

    render(<TextOutput block={block} />)

    expect(screen.getByRole('heading', { name: 'Task status:' })).toBeInTheDocument()
    expect(screen.getByText(/Complete the fields below to continue/)).toBeInTheDocument()
  })

  it('renders inline reference links inside the paragraph', () => {
    render(
      <TextOutput
        block={{
          id: 'preview-intro',
          type: 'text',
          content:
            'The minimum required wall thickness for straight pipe under internal pressure shall be computed based on',
          content_suffix: ' with the following equation:',
          variant: 'body',
          reference_links: [{ node_id: 'B313-304.1.2', label: '§304.1.2' }],
          reference_links_placement: 'inline',
        }}
      />,
    )

    expect(screen.getByRole('button', { name: '§304.1.2' })).toBeInTheDocument()
    expect(screen.getByText(/with the following equation:/)).toBeInTheDocument()
    expect(screen.queryByText('Straight Pipe Under Internal Pressure')).not.toBeInTheDocument()
  })
})

describe('OutputRenderer', () => {
  it('shows placeholder when there are no blocks', () => {
    render(<OutputRenderer blocks={[]} emptyMessage="No outputs yet." />)

    expect(screen.getByText('No outputs yet.')).toBeInTheDocument()
  })

  it('renders mixed engineering output blocks', () => {
    render(<OutputRenderer blocks={mockTaskState.display_outputs} />)

    expect(screen.getByText('Task status:')).toBeInTheDocument()
    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(
      screen.getByText(/minimum required wall thickness for straight pipe under internal pressure/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '§304.1.2' })).toBeInTheDocument()
  })

  it('shows value_reference links for derived equation input values', () => {
    render(
      <OutputRenderer
        blocks={[
          {
            id: 'preview-equation',
            type: 'equation',
            content: 't = PD / 2(SEW + PY)',
            display: 't = PD / 2(SEW + PY)',
            input_table: {
              columns: [
                { key: 'symbol', label: 'Symbol', sortable: false },
                { key: 'definition', label: 'Definition', sortable: false },
                { key: 'value', label: 'Value', sortable: false },
              ],
              rows: [
                {
                  symbol: 'S',
                  definition: 'Allowable stress',
                  value: '',
                  value_reference: { node_id: 'B313-table-A-1', label: 'Table A-1' },
                },
              ],
            },
          },
        ]}
      />,
    )

    expect(screen.getByRole('button', { name: 'Table A-1' })).toBeInTheDocument()
    expect(screen.queryByText('Awaiting user input')).not.toBeInTheDocument()
  })
})
