import { describe, expect, it } from 'vitest'

import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('mergeDisplayOutputs', () => {
  it('appends new blocks while keeping previous ones', () => {
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

    expect(merged).toEqual([previous, incoming])
  })

  it('updates overlapping ids in place without removing other blocks', () => {
    const previous: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      title: null,
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const retained: DisplayOutputBlock = {
      id: 'node-activation-equation-B313-304.1.1-0',
      type: 'equation',
      title: 'Required thickness',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }
    const incoming: DisplayOutputBlock = {
      ...previous,
      display: '0.259 mm  t = (900000)(114.3) / 2(...)',
    }

    const merged = mergeDisplayOutputs([retained, previous], [incoming])

    expect(merged).toHaveLength(2)
    expect(merged[0]).toEqual(retained)
    expect(merged[1]?.display).toBe('0.259 mm  t = (900000)(114.3) / 2(...)')
  })

  it('keeps previous blocks when the backend snapshot is empty', () => {
    const previous: DisplayOutputBlock = {
      id: 'planning-status',
      type: 'text',
      content: 'Awaiting input',
    }

    const merged = mergeDisplayOutputs([previous], [])

    expect(merged).toEqual([previous])
  })
})
