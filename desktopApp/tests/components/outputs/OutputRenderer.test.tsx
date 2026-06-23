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

    expect(screen.getByRole('heading', { name: 'Task status' })).toBeInTheDocument()
    expect(screen.getByText(/Waiting for inputs: nominal_pipe_size/)).toBeInTheDocument()
  })
})

describe('OutputRenderer', () => {
  it('shows placeholder when there are no blocks', () => {
    render(<OutputRenderer blocks={[]} emptyMessage="No outputs yet." />)

    expect(screen.getByText('No outputs yet.')).toBeInTheDocument()
  })

  it('renders mixed engineering output blocks', () => {
    render(<OutputRenderer blocks={mockTaskState.display_outputs} />)

    expect(screen.getByText('Task status')).toBeInTheDocument()
    expect(screen.getByText('Governing equation')).toBeInTheDocument()
    expect(screen.getByText('Straight Pipe Under Internal Pressure')).toBeInTheDocument()
  })
})
