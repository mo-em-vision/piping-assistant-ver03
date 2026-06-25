import { describe, expect, it } from 'vitest'

import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('mergeDisplayOutputs', () => {
  it('preserves earlier blocks when the backend omits them from a later response', () => {
    const definitionBlock: DisplayOutputBlock = {
      id: 'node-activation-equation-B313-304.1.1-0',
      type: 'equation',
      title: 'Required thickness',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }
    const previewBlock: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      title: null,
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }

    const merged = mergeDisplayOutputs([definitionBlock], [previewBlock])

    expect(merged.map((block) => block.id)).toEqual([
      'node-activation-equation-B313-304.1.1-0',
      'path-preview-equation-B313-304.1.2',
    ])
  })

  it('updates blocks that share an id with the incoming payload', () => {
    const previous: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      title: null,
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const incoming: DisplayOutputBlock = {
      ...previous,
      display: 't = 2.25 mm',
    }

    const merged = mergeDisplayOutputs([previous], [incoming])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.display).toBe('t = 2.25 mm')
  })
})
