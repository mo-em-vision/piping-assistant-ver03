import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FactsTable } from '@dev-ui/inspector/FactsTable'
import { TraceTimelinePanel } from '@dev-ui/inspector/TraceTimelinePanel'

describe('TaskStatePanels', () => {
  it('renders facts table with source and status', () => {
    render(
      <FactsTable
        rows={[
          {
            field: 'allowable_stress',
            label: 'Allowable Stress',
            symbol: 'S',
            value: 138,
            unit: 'MPa',
            source: 'lookup',
            status: 'confirmed',
            parameter_node_id: 'PARAM-allowable-stress',
          },
        ]}
      />,
    )
    expect(screen.getByText('Allowable Stress')).toBeInTheDocument()
    expect(screen.getByText('lookup')).toBeInTheDocument()
    expect(screen.getByText('confirmed')).toBeInTheDocument()
  })

  it('renders trace timeline labels', () => {
    render(
      <TraceTimelinePanel
        rows={[
          {
            order: 1,
            event_type: 'calculation_completed',
            label: 'Calculation completed',
            node_id: 'EQ-1',
            message: 'Node: EQ-1',
            source: 'execution',
          },
        ]}
      />,
    )
    expect(screen.getByText('Calculation completed')).toBeInTheDocument()
    expect(screen.getByText('EQ-1')).toBeInTheDocument()
  })
})
