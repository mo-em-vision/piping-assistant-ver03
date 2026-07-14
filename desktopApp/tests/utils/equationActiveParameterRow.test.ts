import { describe, expect, it } from 'vitest'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { EquationOutputBlock } from '@/types/backend/outputs'
import {
  findActiveEquationRowIndex,
  isActivePreviewEquationBlock,
} from '@/utils/equationActiveParameterRow'

function mockParameter(
  name: string,
  nodeId: string,
): ParameterDefinitionDto {
  return {
    name,
    label: name,
    type: 'number',
    required: true,
    units: [],
    default_unit: 'dimensionless',
    default_value: null,
    value: null,
    options: null,
    validation: null,
    status: 'pending',
    requires_confirmation: false,
    provenance: {
      node_id: nodeId,
      hover_excerpt: 'test',
    },
  }
}

function mockEquationBlock(
  rows: EquationOutputBlock['input_table'] extends infer T ? NonNullable<T>['rows'] : never,
): EquationOutputBlock {
  return {
    id: 'equation-eq-3a',
    type: 'equation',
    display_state: 'preview',
    content: 't = PD / 2(SEW + PY)',
    input_table: {
      columns: [
        { key: 'symbol', label: 'Symbol', sortable: false },
        { key: 'parameter', label: 'Parameter', sortable: false },
        { key: 'value', label: 'Value', sortable: false },
      ],
      rows,
    },
    equation_display_trace: {
      equation_id: 'eq-3a',
      node_id: '304.1.2-a',
      symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
      substituted_latex: 't = \\frac{8D}{2(SEW + PY)}',
      status: 'blocked',
      inputs: [
        { symbol: 'P', parameter_id: 'PARAM-P', label: 'Pressure' },
        { symbol: 'D', parameter_id: 'PARAM-D', label: 'Diameter' },
      ],
      intermediate_values: [],
      result: null,
      latex_source: 'metadata_display_latex',
    },
  }
}

describe('equationActiveParameterRow', () => {
  it('matches row by parameter_id against parameter provenance node_id', () => {
    const block = mockEquationBlock([
      { symbol: 'P', parameter_id: 'PARAM-P', value: 'Awaiting user input' },
      { symbol: 'D', parameter_id: 'PARAM-D', value: '114.3' },
    ])

    expect(findActiveEquationRowIndex(block, mockParameter('internal_design_gage_pressure', 'PARAM-P'))).toBe(0)
    expect(findActiveEquationRowIndex(block, mockParameter('outside_diameter', 'PARAM-D'))).toBe(1)
  })

  it('matches row via value_provenance source_ref parameter_id', () => {
    const block = mockEquationBlock([
      {
        symbol: 'P',
        value: 'Awaiting user input',
        value_provenance: {
          source_type: 'user_input',
          status: 'awaiting_user_input',
          label: 'User input',
          source_ref: { parameter_id: 'PARAM-P' },
        },
      },
    ])

    expect(findActiveEquationRowIndex(block, mockParameter('internal_design_gage_pressure', 'PARAM-P'))).toBe(0)
  })

  it('matches row via equation_display_trace inputs when row lacks parameter_id', () => {
    const block = mockEquationBlock([
      { symbol: 'D', value: 'Awaiting user input' },
    ])

    expect(findActiveEquationRowIndex(block, mockParameter('outside_diameter', 'PARAM-D'))).toBe(0)
  })

  it('returns null when parameter does not match any row', () => {
    const block = mockEquationBlock([
      { symbol: 'P', parameter_id: 'PARAM-P', value: '8' },
    ])

    expect(findActiveEquationRowIndex(block, mockParameter('material_grade', 'PARAM-MAT'))).toBeNull()
    expect(findActiveEquationRowIndex(block, null)).toBeNull()
  })

  it('identifies preview and active equation blocks', () => {
    const block = mockEquationBlock([{ symbol: 'P', parameter_id: 'PARAM-P' }])

    expect(isActivePreviewEquationBlock({ ...block, display_state: 'preview' })).toBe(true)
    expect(isActivePreviewEquationBlock({ ...block, display_state: 'active' })).toBe(true)
    expect(isActivePreviewEquationBlock({ ...block, display_state: 'evaluated' })).toBe(false)
    expect(isActivePreviewEquationBlock({ ...block, type: 'text', content: 'x' } as never)).toBe(false)
  })
})
