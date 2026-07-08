import { beforeEach, describe, expect, it } from 'vitest'

import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

describe('performanceTraceStore', () => {
  beforeEach(() => {
    usePerformanceTraceStore.getState().reset()
  })

  it('begins an interaction with a frontend-owned trace id', () => {
    const traceId = usePerformanceTraceStore.getState().beginInteraction('submit_input', 'task-1')

    expect(traceId).toMatch(/^[0-9a-f]{16}$/)
    const trace = usePerformanceTraceStore.getState().getTrace(traceId)
    expect(trace?.trigger).toBe('submit_input')
    expect(trace?.task_id).toBe('task-1')
    expect(usePerformanceTraceStore.getState().activeTraceId).toBe(traceId)
  })

  it('records frontend spans on the active trace', () => {
    const traceId = usePerformanceTraceStore.getState().beginInteraction('submit_input', 'task-1')

    usePerformanceTraceStore.getState().recordFrontendSpan(traceId, {
      name: 'frontend_state_update',
      duration_ms: 12.4,
    })

    const trace = usePerformanceTraceStore.getState().getTrace(traceId)
    expect(trace?.spans).toHaveLength(1)
    expect(trace?.spans[0]?.name).toBe('frontend_state_update')
    expect(trace?.spans[0]?.op_type).toBe('frontend')
  })

  it('keeps inspection poll traces separate from submit traces', () => {
    const submitTraceId = usePerformanceTraceStore.getState().beginInteraction('submit_input', 'task-1')
    const pollTraceId = usePerformanceTraceStore.getState().beginInteraction('inspection_poll', 'task-1')

    expect(submitTraceId).not.toBe(pollTraceId)
    expect(usePerformanceTraceStore.getState().getTraces()).toHaveLength(2)
    expect(usePerformanceTraceStore.getState().getTrace(pollTraceId)?.trigger).toBe('inspection_poll')
  })
})
