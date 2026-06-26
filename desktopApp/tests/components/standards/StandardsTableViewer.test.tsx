import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StandardsTableViewer } from '@/components/standards/StandardsTableViewer'
import type { TableSourceDto } from '@/types/backend/api'

const SAMPLE_TABLE: TableSourceDto = {
  table_id: 'demo-table',
  title: 'Demo Lookup Table',
  standard: 'ASME B31.3',
  source_path: 'Table Demo',
  columns: [
    { key: 'material', label: 'Material' },
    { key: 'temp_f', label: 'Temp (F)' },
    { key: 'value', label: 'Value' },
  ],
  rows: [
    { material: 'Carbon Steel', temp_f: '300', value: '0.4' },
    { material: 'Carbon Steel', temp_f: '500', value: '0.5' },
    { material: 'Stainless Steel', temp_f: '300', value: '0.45' },
  ],
  hover_excerpt: 'Demo table',
}

const TABLE_304: TableSourceDto = {
  table_id: 'asme_b31.3_table_304_1_1',
  title: 'Table 304.1.1 — Temperature Coefficient Y',
  standard: 'ASME B31.3',
  source_path: 'asme_b313_tables.db',
  columns: [
    { key: 'material', label: 'Material' },
    { key: 'material_id', label: 'Material ID' },
    { key: 'temperature_c', label: 'Temperature (°C)' },
    { key: 'design_temperature', label: 'Design Temperature (°F)' },
    { key: 'coefficient_Y', label: 'Coefficient Y' },
  ],
  rows: [
    {
      material: 'Ferritic steels',
      material_id: 'ferritic_steels',
      temperature_c: 482,
      design_temperature: 899.6,
      coefficient_Y: 0.4,
    },
    {
      material: 'Ferritic steels',
      material_id: 'ferritic_steels',
      temperature_c: 510,
      design_temperature: 950,
      coefficient_Y: 0.5,
    },
    {
      material: 'Austenitic steels',
      material_id: 'austenitic_steels',
      temperature_c: 482,
      design_temperature: 899.6,
      coefficient_Y: 0.4,
    },
  ],
  hover_excerpt: 'Table 304.1.1',
}

describe('StandardsTableViewer', () => {
  it('hides internal columns such as material_id from the table view', () => {
    render(<StandardsTableViewer payload={TABLE_304} />)

    expect(screen.getByRole('columnheader', { name: 'Material' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Coefficient Y' })).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Material ID' })).not.toBeInTheDocument()
    expect(screen.queryByText('ferritic_steels')).not.toBeInTheDocument()
    expect(screen.getAllByText('Ferritic steels').length).toBeGreaterThan(0)
  })

  it('filters rows using per-column header filters', () => {
    render(<StandardsTableViewer payload={TABLE_304} />)

    fireEvent.change(screen.getByLabelText('Filter Coefficient Y'), {
      target: { value: '0.5' },
    })

    expect(screen.getByText('1 of 3 rows')).toBeInTheDocument()
    expect(screen.getByText('0.5')).toBeInTheDocument()
    expect(screen.queryByText('Austenitic steels')).not.toBeInTheDocument()
  })

  it('filters rows by material using column filters', () => {
    render(<StandardsTableViewer payload={SAMPLE_TABLE} />)

    fireEvent.change(screen.getByLabelText('Filter Material'), {
      target: { value: 'Stainless' },
    })

    expect(screen.getByText('1 of 3 rows')).toBeInTheDocument()
    expect(screen.getByText('Stainless Steel')).toBeInTheDocument()
    expect(screen.queryByText('0.5')).not.toBeInTheDocument()
  })

  it('shows all rows when only temperature highlight context is provided', () => {
    render(
      <StandardsTableViewer
        payload={TABLE_304}
        viewerContext={{
          highlightKeys: { design_temperature: '950' },
        }}
      />,
    )

    expect(screen.getByText('3 of 3 rows')).toBeInTheDocument()
    expect(screen.getByText('950')).toBeInTheDocument()
    expect(screen.getByText('0.5')).toBeInTheDocument()
  })

  it('highlights rows that match viewer context keys', () => {
    const { container } = render(
      <StandardsTableViewer
        payload={SAMPLE_TABLE}
        viewerContext={{
          highlightKeys: { material: 'Carbon Steel', temp_f: '500' },
        }}
      />,
    )

    const highlighted = container.querySelector('.standards-table-viewer__row--highlighted')
    expect(highlighted).toBeTruthy()
    expect(highlighted).toHaveTextContent('500')
    expect(highlighted).toHaveTextContent('0.5')
  })

  it('keeps column headers visible when filters exclude all rows', () => {
    render(<StandardsTableViewer payload={SAMPLE_TABLE} />)

    fireEvent.change(screen.getByLabelText('Filter Material'), {
      target: { value: 'no-match' },
    })

    expect(screen.getByText('0 of 3 rows')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Material' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Temp (F)' })).toBeInTheDocument()
    expect(screen.getByLabelText('Filter Material')).toHaveValue('no-match')
    expect(screen.getByText('No rows match the current filters.')).toBeInTheDocument()
  })
})
