import { describe, expect, it } from 'vitest'

import {
  inferDisplayState,
  isCanonicalDisplayRole,
  lifecycleForEquationState,
  resolveDisplayBlock,
} from '@/utils/displayRole'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('displayRole', () => {
  it('recognizes canonical roles only', () => {
    expect(isCanonicalDisplayRole('equation')).toBe(true)
    expect(isCanonicalDisplayRole('calculation_trace')).toBe(false)
    expect(isCanonicalDisplayRole('equation_trace')).toBe(false)
  })

  it('resolves equation preview from path-preview id', () => {
    const block: DisplayOutputBlock = {
      id: 'path-preview-equation-304.1.2-a',
      type: 'equation',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const resolved = resolveDisplayBlock(block)
    expect(resolved.display_role).toBe('equation')
    expect(resolved.display_state).toBe('preview')
    expect(resolved.lifecycle).toBe('preview')
  })

  it('resolves evaluated equation from stable id', () => {
    const block: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-1-eq-2',
      type: 'equation',
      display_role: 'equation',
      display_state: 'evaluated',
      equation_content: 'evaluated',
      content: 't_m = 2.252',
      display: 't_m = 2.252',
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-1-eq-2',
        node_id: '304.1.1-a',
        symbolic_latex: 't_m = t + c',
        latex_source: 'metadata_display_text',
        status: 'evaluated',
        inputs: [],
        intermediate_values: [],
      },
    }
    expect(lifecycleForEquationState(inferDisplayState(block))).toBe('durable')
    expect(resolveDisplayBlock(block).lifecycle).toBe('durable')
  })
})
