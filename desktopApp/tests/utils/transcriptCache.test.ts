import { beforeEach, describe, expect, it } from 'vitest'

import type { DisplayOutputBlock } from '@/types/backend/outputs'
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
