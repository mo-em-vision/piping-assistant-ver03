import { beforeEach, describe, expect, it } from 'vitest'

import type { DisplayOutputBlock } from '@/types/backend/outputs'
import { durableDisplayBlocks } from '@/utils/displayBlockLifecycle'
import {
  clearTranscriptCache,
  loadTranscriptCache,
  saveTranscriptCache,
} from '@/utils/transcriptCache'

const sampleBlock: DisplayOutputBlock = {
  id: 'preview-equation',
  type: 'equation',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
}

describe('transcriptCache', () => {
  beforeEach(() => {
    clearTranscriptCache()
    sessionStorage.clear()
  })

  it('round-trips transcript blocks per task id', () => {
    saveTranscriptCache('task-1', [sampleBlock])

    expect(loadTranscriptCache('task-1')).toEqual([sampleBlock])
    expect(loadTranscriptCache('task-2')).toEqual([])
  })

  it('stores durable equation traces and drops preview-only blocks', () => {
    const trace: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-1-eq-2',
      type: 'equation',
      lifecycle: 'durable',
      display_role: 'equation',
      display_state: 'evaluated',
      equation_node_id: 'asme-b313-304-1-1-eq-2',
      source_node_id: '304.1.1-a',
      content: 't_m = t + c',
      display: 't_m = t + c',
      input_table: {
        columns: [
          { key: 'symbol', label: 'Symbol', sortable: false },
          { key: 'definition', label: 'Definition', sortable: false },
          { key: 'value', label: 'Value', sortable: false },
        ],
        rows: [{ symbol: 't', definition: 'Required thickness', value: '2.000 mm' }],
      },
    }
    const preview: DisplayOutputBlock = {
      id: 'path-preview-equation-304.1.1-a',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      display_channel: 'current_equation_preview',
      content: 't_m = t + c',
      display: 't_m = t + c',
    }

    saveTranscriptCache('task-trace', durableDisplayBlocks([trace, preview]))
    expect(loadTranscriptCache('task-trace')).toEqual([trace])
  })

  it('clears one task without affecting others', () => {
    saveTranscriptCache('task-1', [sampleBlock])
    saveTranscriptCache('task-2', [
      { id: 'status', type: 'text', content: 'Status' },
    ])

    clearTranscriptCache('task-1')

    expect(loadTranscriptCache('task-1')).toEqual([])
    expect(loadTranscriptCache('task-2')).toHaveLength(1)
  })
})
