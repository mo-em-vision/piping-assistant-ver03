import { beforeEach, describe, expect, it, vi } from 'vitest'

import { installFetchMock } from '../../helpers/apiMocks'
import { PERFORMANCE_TRACE_HEADER } from '@/services/performance/traceId'
import { tracedRequest } from '@/services/performance/tracedRequest'
import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

describe('tracedRequest', () => {
  beforeEach(() => {
    usePerformanceTraceStore.getState().reset()
    vi.restoreAllMocks()
  })

  it('sends the performance trace header and records frontend request spans', async () => {
    const traceId = '1234567890abcdef'
    usePerformanceTraceStore.getState().ensureTrace(traceId, 'submit_input', 'task-1')

    installFetchMock({
      '/api/v1/tasks/task-1/inputs': () =>
        new Response(
          JSON.stringify({
            task_id: 'task-1',
            performance_trace: {
              trace_id: traceId,
              trigger: 'submit_input',
              task_id: 'task-1',
              total_duration_ms: 250,
              llm_call_occurred: false,
              status: 'success',
              error: null,
              spans_omitted: 0,
              spans: [],
            },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
    })

    await tracedRequest(
      '/api/v1/tasks/task-1/inputs',
      { method: 'POST', body: { parameter: 'nominal_pipe_size', value: 4 } },
      { traceId, trigger: 'submit_input', taskId: 'task-1' },
    )

    const fetchCall = vi.mocked(global.fetch).mock.calls[0]
    const init = fetchCall[1] as RequestInit
    expect((init.headers as Record<string, string>)[PERFORMANCE_TRACE_HEADER]).toBe(traceId)

    const trace = usePerformanceTraceStore.getState().getTrace(traceId)
    expect(trace?.spans.map((span) => span.name)).toEqual(['request_sent', 'response_received'])
    expect(trace?.spans.every((span) => span.op_type === 'frontend')).toBe(true)
  })

  it('finalizes inspection poll traces without stealing the active submit trace', async () => {
    const submitTraceId = usePerformanceTraceStore.getState().beginInteraction('submit_input', 'task-1')
    const pollTraceId = 'abcdef1234567890'

    installFetchMock({
      '/api/v1/tasks/task-1/inspection': () =>
        new Response(JSON.stringify({ task_id: 'task-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    })

    await tracedRequest(
      '/api/v1/tasks/task-1/inspection',
      { method: 'GET' },
      { traceId: pollTraceId, trigger: 'inspection_poll', taskId: 'task-1', preserveActiveTrace: true },
    )

    expect(usePerformanceTraceStore.getState().activeTraceId).toBe(submitTraceId)
    expect(usePerformanceTraceStore.getState().getTrace(pollTraceId)?.status).toBe('success')
    expect(usePerformanceTraceStore.getState().getTrace(submitTraceId)?.status).toBe('running')
  })
})
