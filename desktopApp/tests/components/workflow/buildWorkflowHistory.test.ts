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

    const items = buildWorkflowHistory(
      viewModel!.timeline,
      mockTaskState.display_outputs,
      mockTaskState.inputs,
      mockTaskState.parameters,
    )

    expect(items.some((item) => item.kind === 'prompt' && item.title === 'Material')).toBe(true)
    expect(items.some((item) => item.kind === 'user-input' && item.value === 'SA-106B')).toBe(true)
    expect(items.some((item) => item.kind === 'prompt' && item.title === 'Thickness')).toBe(true)
    expect(items.some((item) => item.kind === 'output' && item.block.id === 'preview-equation')).toBe(
      true,
    )
    expect(items.some((item) => item.kind === 'prompt' && item.title === 'Report')).toBe(false)
  })
})

describe('getCurrentEditableParameter', () => {
  it('returns the first pending parameter', () => {
    const parameter = getCurrentEditableParameter(mockTaskState)
    expect(parameter?.name).toBe('nominal_pipe_size')
  })
})
