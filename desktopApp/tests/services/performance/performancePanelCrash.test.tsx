import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PerformanceTracePanel } from '@dev-ui/inspector/PerformanceTracePanel'
import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

const getPerformanceTraces = vi.fn()

vi.mock('@/services/api/inspectionApi', () => ({
  inspectionApi: {
    getPerformanceTraces: (...args: unknown[]) => getPerformanceTraces(...args),
  },
}))

describe('PerformanceTracePanel crash paths', () => {
  beforeEach(() => {
    usePerformanceTraceStore.getState().reset()
    vi.clearAllMocks()
  })

  it('survives API traces missing spans array', async () => {
    getPerformanceTraces.mockResolvedValue({
      traces: [
        {
          trace_id: 'abcd1234efgh5678',
          trigger: 'submit_input',
          task_id: 'task-1',
          total_duration_ms: 100,
          llm_call_occurred: false,
          status: 'success',
          error: null,
          spans_omitted: 0,
          spans: undefined,
        },
      ],
    })

    expect(() => render(<PerformanceTracePanel />)).not.toThrow()
    expect(await screen.findByText('Performance Trace')).toBeInTheDocument()
  })
})
