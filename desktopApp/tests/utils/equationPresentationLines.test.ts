import { describe, expect, it } from 'vitest'

import { equationPresentationLines } from '@/utils/equationPresentationLines'
import type { EquationOutputBlock } from '@/types/backend/outputs'

describe('equationPresentationLines', () => {
  it('keeps output symbol on substituted line during blocked partial substitution', () => {
    const block: EquationOutputBlock = {
      id: 'eq-2-partial',
      type: 'equation',
      equation_display_trace: {
        equation_id: 'eq-2',
        node_id: '304.1.1-a',
        symbolic_latex: 't_m = t + c',
        substituted_latex: 't_m = (2) + c',
        result_latex: null,
        latex_source: 'metadata_display_text',
        status: 'blocked',
        inputs: [],
        intermediate_values: [],
        result: null,
      },
    }

    const lines = equationPresentationLines(block)
    expect(lines.symbolic).toBe('t_m = t + c')
    expect(lines.substituted).toBe('t_m = (2) + c')
    expect(lines.substituted?.startsWith('t_m')).toBe(true)
    expect(lines.result).toBeNull()
  })

  it('splits substituted and result lines for evaluated traces', () => {
    const block: EquationOutputBlock = {
      id: 'eq-1',
      type: 'equation',
      equation_display_trace: {
        equation_id: 'eq-1',
        node_id: '304.1.2-a',
        symbolic_latex: 't_m = t + c',
        substituted_latex: 't_m = 1.2 + 0.5 = 1.7\\ \\mathrm{mm}',
        result_latex: '1.7\\ \\mathrm{mm}',
        latex_source: 'metadata_display_text',
        status: 'evaluated',
        inputs: [],
        intermediate_values: [],
        result: {
          symbol: 't_m',
          value: 1.7,
          unit: 'mm',
          display_value: '1.7\\ \\mathrm{mm}',
        },
      },
    }

    const lines = equationPresentationLines(block)
    expect(lines.symbolic).toBe('t_m = t + c')
    expect(lines.substituted).toBe('t_m = 1.2 + 0.5')
    expect(lines.result).toBe('t_m = 1.7\\ \\mathrm{mm}')
  })
})
