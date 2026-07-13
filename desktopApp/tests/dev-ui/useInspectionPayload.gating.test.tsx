import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getTraced = vi.fn()
const useTaskStoreMock = vi.fn()

vi.mock('@/services/api/inspectionApi', () => ({
  inspectionApi: {
    getTraced: (...args: unknown[]) => getTraced(...args),
    createInspectionPollTraceId: () => 'abcdef1234567890',
  },
}))

vi.mock('@/store/taskStore', () => ({
  useTaskStore: (selector: (state: { activeTask: { id: string } | null; sessionId: string | null }) => unknown) =>
    useTaskStoreMock(selector),
}))

describe('useInspectionPayload gating', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getTraced.mockResolvedValue({
      task_id: 'task-1',
      planner_debug_projection: {
        goals: { main_goal: 'Pipe Wall Thickness Design', subgoals: [] },
        groups: {},
      },
    })
    useTaskStoreMock.mockImplementation(
      (selector: (state: { activeTask: { id: string } | null; sessionId: string | null }) => unknown) =>
        selector({ activeTask: null, sessionId: null }),
    )
  })

  it('does not poll inspection when the hook is not mounted', () => {
    expect(getTraced).not.toHaveBeenCalled()
  })

  it('polls inspection only when a dev tab hook mounts with an active task', async () => {
    useTaskStoreMock.mockImplementation(
      (selector: (state: { activeTask: { id: string } | null; sessionId: string | null }) => unknown) =>
        selector({ activeTask: { id: 'task-1' }, sessionId: 'session-1' }),
    )

    const { useInspectionPayload } = await import('@dev-ui/inspector/useInspectionPayload')
    renderHook(() => useInspectionPayload(60_000))

    await waitFor(() => {
      expect(getTraced).toHaveBeenCalledWith('task-1', 'abcdef1234567890', 'session-1')
    })
  })
})
