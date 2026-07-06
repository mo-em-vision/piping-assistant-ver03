import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OperationTrackerPanel } from '../inspector/OperationTrackerPanel'

const getOperations = vi.fn()

vi.mock('@/services/api/inspectionApi', () => ({
  inspectionApi: {
    getOperations: (...args: unknown[]) => getOperations(...args),
  },
}))

describe('OperationTrackerPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows running operations with durations', async () => {
    getOperations.mockResolvedValue({
      running: [
        {
          id: 'op-1',
          name: 'refresh_task_planning',
          category: 'planning',
          status: 'running',
          elapsed_ms: 120.5,
          started_at: 1,
          metadata: { task_id: 'task-abc' },
        },
      ],
      recent: [
        {
          id: 'op-0',
          name: 'POST /api/v1/tasks/task-abc/inputs',
          category: 'http',
          status: 'completed',
          duration_ms: 450.2,
          started_at: 0,
          finished_at: 1,
        },
      ],
    })

    render(<OperationTrackerPanel />)

    expect(await screen.findByText('refresh_task_planning')).toBeInTheDocument()
    expect(screen.getByText('120.5 ms')).toBeInTheDocument()
    expect(screen.getByText('POST /api/v1/tasks/task-abc/inputs')).toBeInTheDocument()
    expect(screen.getByText('450.2 ms')).toBeInTheDocument()
  })

  it('shows idle state when nothing is running', async () => {
    getOperations.mockResolvedValue({ running: [], recent: [] })

    render(<OperationTrackerPanel />)

    expect(await screen.findByText('No active backend work.')).toBeInTheDocument()
  })
})
