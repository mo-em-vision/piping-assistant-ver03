import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PerformanceTracePanel } from '../inspector/PerformanceTracePanel'

const getPerformanceTraces = vi.fn()

vi.mock('@/services/api/inspectionApi', () => ({
  inspectionApi: {
    getPerformanceTraces: (...args: unknown[]) => getPerformanceTraces(...args),
  },
}))

vi.mock('@/store/performanceTraceStore', () => {
  const state = {
    traceOrder: [] as string[],
    tracesById: {} as Record<string, unknown>,
    ingestPolledTraces: vi.fn(),
    getTraces: () => [],
  }
  const usePerformanceTraceStore = (selector: (value: typeof state) => unknown) => selector(state)
  usePerformanceTraceStore.getState = () => state
  return { usePerformanceTraceStore }
})

const SAMPLE_TRACE = {
  trace_id: 'abcd1234efgh5678',
  trigger: 'POST /api/v1/tasks/task-1/inputs',
  task_id: 'task-1',
  total_duration_ms: 1250.4,
  llm_call_occurred: false,
  status: 'success',
  error: null,
  spans_omitted: 0,
  spans: [
    {
      span_id: 'span-1',
      parent_span_id: null,
      name: 'task_state',
      op_type: 'serializer',
      duration_ms: 620.2,
      status: 'success',
      llm: false,
      notes: null,
    },
    {
      span_id: 'span-2',
      parent_span_id: null,
      name: 'refresh_task_planning',
      op_type: 'planner',
      duration_ms: 150.1,
      status: 'success',
      llm: false,
      notes: 'propose_defaults=true',
    },
  ],
}

const POLL_TRACE = {
  trace_id: '1111222233334444',
  trigger: 'inspection_poll',
  task_id: 'task-1',
  total_duration_ms: 340.5,
  llm_call_occurred: false,
  status: 'success',
  error: null,
  spans_omitted: 0,
  spans: [
    {
      span_id: 'span-poll',
      parent_span_id: null,
      name: 'build_inspection_payload',
      op_type: 'serializer',
      duration_ms: 320.0,
      status: 'success',
      llm: false,
      notes: null,
    },
  ],
}

describe('PerformanceTracePanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders trace summary, spans, and severity classes', async () => {
    getPerformanceTraces.mockResolvedValue({ traces: [SAMPLE_TRACE] })

    render(<PerformanceTracePanel />)

    expect(await screen.findByText('Performance Trace')).toBeInTheDocument()
    expect(screen.getByText('abcd1234efgh5678')).toBeInTheDocument()
    expect(screen.getByText('POST /api/v1/tasks/task-1/inputs')).toBeInTheDocument()

    const taskStateRow = screen.getByText('task_state').closest('tr')
    expect(taskStateRow).toHaveClass('perf-trace-row--slow')

    const planningRow = screen.getByText('refresh_task_planning').closest('tr')
    expect(planningRow).toHaveClass('perf-trace-row--watch')
  })

  it('shows inspection poll separation', async () => {
    getPerformanceTraces.mockResolvedValue({
      traces: [{ ...POLL_TRACE, total_duration_ms: 2000 }, SAMPLE_TRACE],
    })

    render(<PerformanceTracePanel />)

    expect(await screen.findByText('Inspection poll')).toBeInTheDocument()
    expect(
      screen.getByText(
        'This trace is from inspection polling and is separate from submit_input workflow steps.',
      ),
    ).toBeInTheDocument()
  })

  it('keeps Advanced JSON collapsed by default', async () => {
    getPerformanceTraces.mockResolvedValue({ traces: [SAMPLE_TRACE] })

    render(<PerformanceTracePanel />)

    const advanced = await screen.findByText('Advanced JSON')
    const details = advanced.closest('details')
    expect(details).toBeTruthy()
    expect(details).not.toHaveAttribute('open')
  })

  it('shows idle state when no traces exist', async () => {
    getPerformanceTraces.mockResolvedValue({ traces: [] })

    render(<PerformanceTracePanel />)

    expect(
      await screen.findByText('Submit a workflow input to record a performance trace.'),
    ).toBeInTheDocument()
  })
})
