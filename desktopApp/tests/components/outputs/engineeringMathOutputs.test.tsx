import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EquationOutput } from '@/components/outputs/EquationOutput'
import { TableOutput } from '@/components/outputs/TableOutput'
import { useRightPanelStore } from '@/store/rightPanelStore'

describe('EquationOutput', () => {
  it('renders equation title and description before symbolic math', () => {
    const { getByText, container } = render(
      <EquationOutput
        block={{
          id: 'eq-heading',
          type: 'equation',
          title: 'Internal Pressure Wall Thickness — Eq. (3a)',
          context_intro: 'Internal pressure design thickness for straight pipe (eq. 3a)',
          content: 't = PD / 2(SEW + PY)',
          display: 't = PD / 2(SEW + PY)',
          equation_display_trace: {
            equation_id: 'eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            status: 'blocked',
            inputs: [],
            intermediate_values: [],
            result: null,
          },
        }}
      />,
    )

    expect(getByText('Internal Pressure Wall Thickness — Eq. (3a)')).toBeTruthy()
    expect(
      getByText('Internal pressure design thickness for straight pipe (eq. 3a)'),
    ).toBeTruthy()
    const math = container.querySelector('.output-equation__math--symbolic')
    expect(math).toBeTruthy()
    expect(
      math!.compareDocumentPosition(getByText('Internal Pressure Wall Thickness — Eq. (3a)'))
        & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy()
  })

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

  it('pins equation number to the panel right while centering symbolic math', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-3a',
          type: 'equation',
          equation_number: '3a',
          content: 't = PD / 2(SEW + PY)',
          display: 't = PD / 2(SEW + PY)',
          equation_display_trace: {
            equation_id: 'asme-b313-304-1-2-eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            status: 'blocked',
            inputs: [],
            intermediate_values: [],
            result: null,
          },
        }}
      />,
    )

    const row = container.querySelector('.output-equation__math-row')
    expect(row).toBeTruthy()
    expect(container.querySelector('.output-equation__math--symbolic')).toBeTruthy()
    expect(container.querySelector('.output-equation__number')?.textContent).toBe('(3a)')
    expect(container.querySelector('.output-equation__math--symbolic .tag')).toBeNull()
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

  it('renders legacy content-only equation as symbolic line', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'equation-trace-304.1.2-a-asme-b313-304-1-2-eq-3a',
          type: 'equation',
          content:
            't = \\frac{(3447378)(254)}{2((193000000)(1)(1) + (3447378)(0.4))} = 2.252\\ \\mathrm{mm}',
          display:
            't = (3447378)(254) / 2((193000000)(1)(1) + (3447378)(0.4)) = 2.252 mm',
        }}
      />,
    )

    expect(container.querySelector('.output-equation--evaluated')).toBeNull()
    expect(container.textContent).toContain('= 2.252')
    expect(container.querySelector('.output-equation__leading-result')).toBeNull()
    expect(container.querySelector('.output-equation__input-table')).toBeNull()
    expect(container.querySelectorAll('.output-equation__math').length).toBe(1)
    expect(container.querySelector('.output-equation__math--symbolic')).toBeTruthy()
  })

  it('opens table references from derived coefficient value links', () => {
    useRightPanelStore.getState().reset(true)

    const { getByRole } = render(
      <EquationOutput
        block={{
          id: 'eq-coefficients',
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
                value_reference: {
                  node_id: 'asme_b31.3_A-1',
                  label: 'Table A-1',
                  reference_kind: 'table',
                },
              },
            ],
          },
        }}
      />,
    )

    getByRole('button', { name: 'Table A-1' }).click()

    const state = useRightPanelStore.getState()
    const refTab = state.tabs.find((tab) => tab.kind === 'reference')
    expect(refTab?.kind).toBe('reference')
    if (refTab?.kind === 'reference') {
      expect(refTab.referenceKind).toBe('table')
      expect(refTab.referenceId).toBe('asme_b31.3_A-1')
      expect(state.activeTabId).toBe(refTab.id)
    }
  })

  it('renders value_provenance pending derived trail with chips', () => {
    const { getByText, getByRole, queryByText } = render(
      <EquationOutput
        block={{
          id: 'eq-provenance',
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
                value_provenance: {
                  source_type: 'table_lookup',
                  status: 'pending_derived',
                  label: 'Resolved from Table A-1',
                  reference_chips: [
                    {
                      ref_type: 'table',
                      id: 'asme_b31.3_A-1',
                      label: 'Table A-1',
                      target: { table_id: 'asme_b31.3_A-1', node_id: 'asme_b31.3_A-1' },
                    },
                  ],
                },
              },
            ],
          },
        }}
      />,
    )

    expect(getByText('Resolved from')).toBeTruthy()
    expect(getByRole('button', { name: 'Table A-1' })).toBeTruthy()
    expect(queryByText('Awaiting user input')).toBeNull()
  })

  it('renders awaiting user input only for true user-input provenance', () => {
    const { container, getByText } = render(
      <EquationOutput
        block={{
          id: 'eq-user-input',
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
                symbol: 'P',
                definition: 'Internal design gage pressure',
                value: 'Awaiting user input',
                value_provenance: {
                  source_type: 'user_input',
                  status: 'awaiting_user_input',
                  label: 'Awaiting user input',
                },
              },
            ],
          },
        }}
      />,
    )

    expect(getByText('Awaiting user input')).toBeTruthy()
    expect(container.querySelector('.output-equation__input-pending')).toBeTruthy()
  })

  it('does not show raw internal ids as primary provenance text', () => {
    const { queryByText, getByRole, getByText } = render(
      <EquationOutput
        block={{
          id: 'eq-chip-label',
          type: 'equation',
          content: 't_m = t + c',
          display: 't_m = t + c',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'definition', label: 'Definition', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
            ],
            rows: [
              {
                symbol: 't',
                definition: 'pressure design thickness',
                value: '',
                value_reference: {
                  node_id: '304.1.2-a',
                  label: 'ASME B31.3 §304.1.2',
                },
              },
            ],
          },
        }}
      />,
    )

    expect(queryByText('304.1.2-a')).toBeNull()
    expect(getByRole('button', { name: 'ASME B31.3 §304.1.2' })).toBeTruthy()
  })

  it('renders derived parameter value references in the value column', () => {
    const { getByRole, getByText, queryByText } = render(
      <EquationOutput
        block={{
          id: 'eq-min-thickness',
          type: 'equation',
          content: 't_m = t + c',
          display: 't_m = t + c',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'definition', label: 'Definition', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
            ],
            rows: [
              {
                symbol: 't',
                definition: 'pressure design thickness',
                value: '',
                value_reference: { node_id: '304.1.2-a', label: '§304.1.2' },
              },
              {
                symbol: 'c',
                definition: 'corrosion allowance',
                value: 'Awaiting user input',
              },
            ],
          },
        }}
      />,
    )

    expect(getByRole('button', { name: '§304.1.2' })).toBeTruthy()
    expect(queryByText('Awaiting user input')).toBeTruthy()
  })

  it('renders inline definition references inside the input table', () => {
    const { getByText, getByRole, queryByText } = render(
      <EquationOutput
        block={{
          id: 'eq-wall-thickness',
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
                symbol: 'D',
                definition: 'Outside diameter of pipe',
                value: '8 bar',
                definition_reference: { node_id: '304.1.1-b', label: '§304.1.1' },
              },
            ],
          },
        }}
      />,
    )

    expect(getByText(/Outside diameter of pipe/)).toBeTruthy()
    expect(getByRole('button', { name: '§304.1.1' })).toBeTruthy()
    expect(queryByText('Symbol definitions:')).toBeNull()
  })

  it('definition column ignores merged reference_chips and keeps value provenance in value column', () => {
    const { getByRole, getAllByRole, queryByRole } = render(
      <EquationOutput
        block={{
          id: 'eq-s-definition',
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
                definition: 'stress value for material',
                value: '',
                definition_reference: { node_id: '304.1.1-b', label: '§304.1.1' },
                reference_chips: [
                  {
                    ref_type: 'table',
                    id: 'asme_b31.3_A-1',
                    label: 'Table A-1',
                    target: { table_id: 'asme_b31.3_A-1', node_id: 'asme_b31.3_A-1' },
                  },
                  {
                    ref_type: 'paragraph',
                    id: '304.1.1-b',
                    label: '§304.1.1',
                    target: { paragraph_id: '304.1.1-b', node_id: '304.1.1-b' },
                  },
                ],
                value_provenance: {
                  source_type: 'table_lookup',
                  status: 'pending_derived',
                  label: 'Resolved from Table A-1',
                  reference_chips: [
                    {
                      ref_type: 'table',
                      id: 'asme_b31.3_A-1',
                      label: 'Table A-1',
                      target: { table_id: 'asme_b31.3_A-1', node_id: 'asme_b31.3_A-1' },
                    },
                  ],
                },
              },
            ],
          },
        }}
      />,
    )

    const definitionLinks = getAllByRole('button', { name: '§304.1.1' })
    expect(definitionLinks).toHaveLength(1)
    expect(getByRole('button', { name: 'Table A-1' })).toBeTruthy()
    expect(queryByRole('button', { name: '§304.1.1-b' })).toBeNull()
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

  it('renders backend equation_display_trace without client-side substitution', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-trace-evaluated',
          type: 'equation',
          content: 'legacy content should not be used',
          equation_display_trace: {
            equation_id: 'eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            substituted_latex: 't = \\frac{(1)(2)}{2((3)(4)(5) + (1)(6))} = 7\\ \\mathrm{mm}',
            result_latex: '7\\ \\mathrm{mm}',
            latex_source: 'metadata_display_text',
            status: 'evaluated',
            inputs: [],
            intermediate_values: [],
            result: {
              symbol: 't',
              value: 7,
              unit: 'mm',
              display_value: '7\\ \\mathrm{mm}',
            },
          },
        }}
      />,
    )

    expect(container.textContent).not.toContain('legacy content')
    expect(container.querySelectorAll('.output-equation__math').length).toBe(3)
    expect(container.querySelector('.output-equation__math--symbolic')).toBeTruthy()
    expect(container.querySelector('.output-equation__math--substituted')).toBeTruthy()
    expect(container.querySelector('.output-equation__math--result')).toBeTruthy()
    expect(container.textContent).toContain('7')
  })

  it('renders symbolic and input table during blocked parameter collection', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-preview-collecting',
          type: 'equation',
          content: 't_m = t + c',
          display: 't_m = t + c',
          equation_display_trace: {
            equation_id: 'eq-2',
            node_id: '304.1.1-a',
            symbolic_latex: 't_m = t + c',
            substituted_latex: null,
            result_latex: null,
            latex_source: 'metadata_display_text',
            status: 'blocked',
            inputs: [],
            intermediate_values: [],
            result: null,
          },
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'definition', label: 'Definition', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
            ],
            rows: [
              { symbol: 't', definition: 'Required thickness', value: 'Awaiting user input' },
            ],
          },
        }}
      />,
    )

    expect(container.querySelector('.output-equation__math--symbolic')).toBeTruthy()
    expect(container.querySelector('.output-equation__input-table')).toBeTruthy()
    expect(container.querySelector('.output-equation__math--substituted')).toBeNull()
    expect(container.querySelector('.output-equation__math--result')).toBeNull()
  })

  it('keeps input table visible after evaluation', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-trace-evaluated-with-table',
          type: 'equation',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'definition', label: 'Definition', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
            ],
            rows: [{ symbol: 'P', definition: 'Design pressure', value: '8 bar' }],
          },
          equation_display_trace: {
            equation_id: 'eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            substituted_latex: 't = \\frac{(8)(2)}{2((3)(4)(5) + (1)(6))}',
            result_latex: '7\\ \\mathrm{mm}',
            latex_source: 'metadata_display_text',
            status: 'evaluated',
            inputs: [],
            intermediate_values: [],
            result: {
              symbol: 't',
              value: 7,
              unit: 'mm',
              display_value: '7\\ \\mathrm{mm}',
            },
          },
        }}
      />,
    )

    expect(container.querySelector('.output-equation__input-table')).toBeTruthy()
    expect(container.querySelectorAll('.output-equation__math').length).toBe(3)
  })

  it('renders evaluated input table beneath the final result line', () => {
    const { container } = render(
      <EquationOutput
        block={{
          id: 'eq-trace-evaluated-order',
          type: 'equation',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'parameter', label: 'Parameter', sortable: false },
              { key: 'description', label: 'Description', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
              { key: 'unit', label: 'Unit', sortable: false },
              { key: 'source', label: 'Source', sortable: false },
            ],
            rows: [
              {
                symbol: 'P',
                parameter: 'Internal Design Gage Pressure',
                description: 'Internal design gage pressure',
                value: '8',
                unit: 'bar',
                source: 'User input',
              },
            ],
          },
          equation_display_trace: {
            equation_id: 'eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            substituted_latex: 't = \\frac{(8)(2)}{2((3)(4)(5) + (1)(6))}',
            result_latex: '7\\ \\mathrm{mm}',
            latex_source: 'metadata_display_text',
            status: 'evaluated',
            inputs: [],
            intermediate_values: [],
            result: {
              symbol: 't',
              value: 7,
              unit: 'mm',
              display_value: '7\\ \\mathrm{mm}',
            },
          },
        }}
      />,
    )

    const mathBlocks = Array.from(container.querySelectorAll('.output-equation__math'))
    const table = container.querySelector('.output-equation__input-table')
    expect(mathBlocks.length).toBe(3)
    expect(table).toBeTruthy()
    const lastMath = mathBlocks[mathBlocks.length - 1]
    expect(lastMath.classList.contains('output-equation__math--result')).toBe(true)
    expect(
      lastMath.compareDocumentPosition(table!) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('renders parameter and description columns from row metadata', () => {
    const { getByText } = render(
      <EquationOutput
        block={{
          id: 'eq-six-column-table',
          type: 'equation',
          input_table: {
            columns: [
              { key: 'symbol', label: 'Symbol', sortable: false },
              { key: 'parameter', label: 'Parameter', sortable: false },
              { key: 'description', label: 'Description', sortable: false },
              { key: 'value', label: 'Value', sortable: false },
              { key: 'unit', label: 'Unit', sortable: false },
              { key: 'source', label: 'Source', sortable: false },
            ],
            rows: [
              {
                symbol: 'P',
                parameter: 'Internal Design Gage Pressure',
                description: 'Internal design gage pressure per design conditions',
                value: '8',
                unit: 'bar',
                source: 'User input',
              },
            ],
          },
          equation_display_trace: {
            equation_id: 'eq-3a',
            node_id: '304.1.2-a',
            symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
            status: 'blocked',
            inputs: [],
            intermediate_values: [],
            result: null,
          },
        }}
      />,
    )

    expect(getByText('Internal Design Gage Pressure')).toBeTruthy()
    expect(getByText('Internal design gage pressure per design conditions')).toBeTruthy()
    expect(getByText('User input')).toBeTruthy()
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
