import { describe, expect, it } from 'vitest'

import { createFrontendSpan, mergeTraceRecords } from '@/services/performance/mergeTraceRecords'

import type { PerformanceTraceDto } from '@/types/backend/inspection'

function baseTrace(overrides: Partial<PerformanceTraceDto> = {}): PerformanceTraceDto {
  return {
    trace_id: 'abcd1234efgh5678',
    trigger: 'submit_input',
    task_id: 'task-1',
    total_duration_ms: 100,
    llm_call_occurred: false,
    status: 'running',
    error: null,
    spans_omitted: 0,
    spans: [],
    ...overrides,
  }
}

describe('mergeTraceRecords', () => {
  it('merges frontend and backend spans by span_id', () => {
    const frontend = baseTrace({
      spans: [createFrontendSpan('request_sent', 0)],
    })
    const backend = baseTrace({
      status: 'success',
      spans: [
        {
          span_id: 'backend-span',
          parent_span_id: null,
          name: 'submit_input',
          op_type: 'api',
          duration_ms: 420,
          status: 'success',
          llm: false,
          notes: null,
        },
      ],
    })

    const merged = mergeTraceRecords(frontend, backend)

    expect(merged.spans).toHaveLength(2)
    expect(merged.status).toBe('success')
    expect(merged.spans.some((span) => span.name === 'request_sent')).toBe(true)
    expect(merged.spans.some((span) => span.name === 'submit_input')).toBe(true)
  })

  it('keeps the higher total duration', () => {
    const frontend = baseTrace({ total_duration_ms: 900 })
    const backend = baseTrace({ total_duration_ms: 1200, status: 'success' })

    const merged = mergeTraceRecords(frontend, backend)

    expect(merged.total_duration_ms).toBe(1200)
  })
})
