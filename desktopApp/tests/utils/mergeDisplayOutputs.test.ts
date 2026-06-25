import { describe, expect, it } from 'vitest'

import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('mergeDisplayOutputs', () => {
  it('replaces previous blocks with the latest backend snapshot', () => {
    const previous: DisplayOutputBlock = {
      id: 'node-activation-equation-B313-304.1.1-0',
      type: 'equation',
      title: 'Required thickness',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }
    const incoming: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      title: null,
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }

    const merged = mergeDisplayOutputs([previous], [incoming])

    expect(merged).toEqual([incoming])
  })

  it('returns incoming blocks even when ids overlap', () => {
    const previous: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      title: null,
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const incoming: DisplayOutputBlock = {
      ...previous,
      display: '0.259 mm  t = (900000)(114.3) / 2(...)',
    }

    const merged = mergeDisplayOutputs([previous], [incoming])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.display).toBe('0.259 mm  t = (900000)(114.3) / 2(...)')
  })
})
