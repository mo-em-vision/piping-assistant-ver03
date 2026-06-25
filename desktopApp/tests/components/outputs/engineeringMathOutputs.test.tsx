import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EquationOutput } from '@/components/outputs/EquationOutput'
import { TableOutput } from '@/components/outputs/TableOutput'

describe('EquationOutput', () => {
  it('renders governing equations with KaTeX only once', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-1',
          type: 'equation',
          title: 'Governing equation',
          content: 't_m = t + c',
          display: 't_m = t + c',
          variables: [{ symbol: 't_m', name: 'Minimum required thickness' }],
        }}
      />,
    )

    expect(container.querySelector('.engineering-math-display .katex')).toBeTruthy()
    expect(container.querySelector('.output-equation__display')).toBeNull()
    expect(container.querySelector('.output-equation__variables .katex')).toBeTruthy()
  })

  it('renders embedded input table with headers and pending values', () => {
    const { container, getByText } = render(
      <EquationOutput
        block={{
          id: 'eq-wall-thickness',
          type: 'equation',
          title: 'Internal Pressure Wall Thickness',
          content: 't = PD / 2(SEW + PY)',
          display: 't = PD / 2(SEW + PY)',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'definition', label: 'Definition', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
            ],
            rows: [
              { symbol: 'P', definition: 'Internal design gage pressure', value: '8 bar' },
              { symbol: 'E', definition: 'Joint efficiency', value: 'Awaiting user input' },
            ],
          },
        }}
      />,
    )

    expect(getByText('Symbol')).toBeTruthy()
    expect(getByText('Definition')).toBeTruthy()
    expect(getByText('Value')).toBeTruthy()
    expect(getByText('Internal design gage pressure')).toBeTruthy()
    expect(getByText('8 bar')).toBeTruthy()
    expect(container.querySelector('.output-equation__input-pending')).toBeTruthy()
    expect(container.querySelector('.output-equation__variables')).toBeNull()
    expect(container.querySelector('.output-equation__input-table .katex')).toBeTruthy()
  })

  it('renders evaluated equation with result and substituted values in one line', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'path-calculation-substituted-equation',
          type: 'equation',
          content: 't = \\frac{(3447378)(254)}{2((193000000)(1)(1) + (3447378)(0.4))}',
          display: '2.252 mm  t = (3447378)(254) / 2((193000000)(1)(1) + (3447378)(0.4))',
          leading_result: { label: 'Required Thickness', value: '2.252', unit: 'mm' },
        }}
      />,
    )

    expect(container.querySelector('.output-equation--evaluated')).toBeTruthy()
    expect(container.textContent).toContain('= 2.252 mm')
    expect(container.querySelector('.output-equation__input-table')).toBeNull()
  })

  it('renders resolved variable descriptions and nomenclature reference link', () => {
    const { getByText, getByRole } = render(
      <EquationOutput
        block={{
          id: 'eq-wall-thickness',
          type: 'equation',
          title: 'Internal Pressure Wall Thickness',
          content: 't = PD / 2(SEW + PY)',
          display: 't = PD / 2(SEW + PY)',
          variables: [{ symbol: 'P', name: 'Internal design gage pressure' }],
          nomenclature_reference: {
            node_id: 'B313-304.1.1',
            label: '§304.1.1(b)',
          },
        }}
      />,
    )

    expect(getByText('Internal design gage pressure')).toBeTruthy()
    expect(getByText(/Symbols defined in/)).toBeTruthy()
    expect(getByRole('button', { name: '§304.1.1(b)' })).toBeTruthy()
  })
})

describe('TableOutput', () => {
  it('renders symbol cells with KaTeX', () => {
    const { container } = render(
      <TableOutput
        block={{
          id: 'table-1',
          type: 'table',
          title: 'Equation parameters',
          columns: [
            { key: 'symbol', label: 'Symbol', sortable: true },
            { key: 'description', label: 'Description', sortable: true },
          ],
          rows: [
            { symbol: 't_m', description: 'Minimum required thickness' },
            { symbol: 'c', description: 'Corrosion allowance' },
          ],
          searchable: false,
        }}
      />,
    )

    const symbolCells = container.querySelectorAll('tbody td:first-child .katex')
    expect(symbolCells.length).toBe(2)
  })

  it('applies compact centered layout when block.compact is true', () => {
    const { container } = render(
      <TableOutput
        block={{
          id: 'table-compact',
          type: 'table',
          columns: [
            { key: 'parameter', label: 'Parameter', sortable: false },
            { key: 'value', label: 'Value', sortable: false },
          ],
          rows: [{ parameter: 'Joint efficiency (E)', value: '1' }],
          searchable: false,
          compact: true,
        }}
      />,
    )

    expect(container.querySelector('.output-block--compact-table')).toBeTruthy()
  })
})
