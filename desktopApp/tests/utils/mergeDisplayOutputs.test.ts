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

  it('appends multiple new blocks in backend order', () => {
    const blockA: DisplayOutputBlock = {
      id: 'explanation-a',
      type: 'text',
      content: 'First explanation',
    }
    const blockB: DisplayOutputBlock = {
      id: 'equation-b',
      type: 'equation',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const blockC: DisplayOutputBlock = {
      id: 'warning-c',
      type: 'text',
      content: 'Check assumptions',
      variant: 'warning',
    }
    const blockD: DisplayOutputBlock = {
      id: 'table-d',
      type: 'table',
      columns: [{ key: 'symbol', label: 'Symbol' }],
      rows: [{ symbol: 'P' }],
    }

    const merged = mergeDisplayOutputs(
      [blockA, blockB],
      [blockC, blockD],
    )

    expect(merged).toEqual([blockA, blockB, blockC, blockD])
  })

  it('updates equation input_table rows in place by id', () => {
    const previous: DisplayOutputBlock = {
      id: 'preview-equation',
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
          { symbol: 'D', definition: 'Outside diameter', value: 'Awaiting user input' },
        ],
      },
    }
    const incoming: DisplayOutputBlock = {
      ...previous,
      input_table: {
        columns: previous.input_table!.columns,
        rows: [{ symbol: 'D', definition: 'Outside diameter', value: '114.3 mm' }],
      },
    }

    const merged = mergeDisplayOutputs([previous], [incoming])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.type).toBe('equation')
    if (merged[0]?.type === 'equation') {
      expect(merged[0].input_table?.rows[0]?.value).toBe('114.3 mm')
    }
  })

  it('does not remove block when backend omits it from snapshot', () => {
    const equation: DisplayOutputBlock = {
      id: 'path-preview-equation-B313-304.1.2',
      type: 'equation',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }
    const explanation: DisplayOutputBlock = {
      id: 'preview-intro',
      type: 'text',
      content: 'The minimum required wall thickness shall be computed.',
    }
    const incoming: DisplayOutputBlock = {
      id: 'planning-status',
      type: 'text',
      content: 'Complete the fields below to continue.',
    }

    const merged = mergeDisplayOutputs([equation, explanation], [incoming])

    expect(merged).toHaveLength(3)
    expect(merged[0]).toEqual(equation)
    expect(merged[1]).toEqual(explanation)
    expect(merged[2]).toEqual(incoming)
  })

  it('returns incoming unchanged when previous is empty', () => {
    const incoming: DisplayOutputBlock[] = [
      {
        id: 'planning-status',
        type: 'text',
        content: 'Awaiting input',
      },
    ]

    expect(mergeDisplayOutputs([], incoming)).toEqual(incoming)
  })

  it('empty incoming snapshot retains all prior blocks', () => {
    const blocks: DisplayOutputBlock[] = [
      { id: 'a', type: 'text', content: 'One' },
      { id: 'b', type: 'text', content: 'Two' },
      { id: 'c', type: 'equation', content: 'x = 1', display: 'x = 1' },
    ]

    expect(mergeDisplayOutputs(blocks, [])).toEqual(blocks)
  })
})
