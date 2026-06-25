import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { NodeCalculationGroup } from '@/components/engineering/NodeCalculationGroup'
import type { NodeCalculationSummaryDto } from '@/types/backend/api'

const summary: NodeCalculationSummaryDto = {
  node_id: 'B313-304.1.2',
  paragraph: '304.1.2',
  title: 'Straight Pipe Under Internal Pressure',
  primary_result: {
    symbol: 't',
    label: 'Required wall thickness',
    value: '0.084',
    unit: 'mm',
  },
  inputs: [
    { symbol: 'P', name: 'Design pressure', value: '8.0', unit: 'bar' },
    { symbol: 'D', name: 'Outside diameter', value: '168.3', unit: 'mm' },
  ],
}

describe('NodeCalculationGroup', () => {
  it('shows collapsed primary result by default', () => {
    render(<NodeCalculationGroup summary={summary} />)

    expect(screen.getByText(/t = 0\.084 mm/)).toBeInTheDocument()
    expect(screen.queryByText('Design pressure')).not.toBeInTheDocument()
  })

  it('expands to show calculation inputs when toggled', () => {
    render(<NodeCalculationGroup summary={summary} />)

    fireEvent.click(screen.getByRole('button', { expanded: false }))

    expect(screen.getByText('Design pressure')).toBeInTheDocument()
    expect(screen.getByText('Outside diameter')).toBeInTheDocument()
    expect(screen.getByText('8.0 bar')).toBeInTheDocument()
  })
})
