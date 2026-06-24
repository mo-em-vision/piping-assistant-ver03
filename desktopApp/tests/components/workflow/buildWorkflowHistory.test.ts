import { describe, expect, it } from 'vitest'

import {
  buildWorkflowHistory,
  getCurrentEditableParameter,
} from '@/components/workflow/buildWorkflowHistory'
import { mockTaskState } from '@/mock/taskState.mock'
import { buildTaskStateViewModel } from '@/store/taskStateManager'

describe('buildWorkflowHistory', () => {
  it('includes completed steps, active step, and outputs up to current phase', () => {
    const viewModel = buildTaskStateViewModel(mockTaskState)
    expect(viewModel).not.toBeNull()

    const items = buildWorkflowHistory(viewModel!.timeline, mockTaskState.display_outputs)

    expect(items.some((item) => item.kind === 'report-statement' && item.body === 'Design material: SA-106B.')).toBe(
      false,
    )
    expect(items.some((item) => item.kind === 'report-statement' && item.body === 'Design pressure: 8 bar.')).toBe(
      false,
    )
    expect(
      items.some(
        (item) =>
          item.kind === 'output' &&
          item.block.type === 'table' &&
          item.block.id.startsWith('path-preview-inputs-table'),
      ),
    ).toBe(false)
    expect(items.some((item) => item.kind === 'output' && item.block.id === 'preview-equation')).toBe(
      true,
    )
    expect(items.some((item) => item.id === 'planning-status')).toBe(false)
    expect(items.some((item) => item.kind === 'next-step')).toBe(false)
  })
})

describe('getCurrentEditableParameter', () => {
  it('returns the first pending parameter', () => {
    const parameter = getCurrentEditableParameter(mockTaskState)
    expect(parameter?.name).toBe('nominal_pipe_size')
  })
})
