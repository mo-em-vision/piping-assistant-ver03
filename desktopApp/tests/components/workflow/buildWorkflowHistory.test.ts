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

    expect(items.some((item) => item.kind === 'report-statement' && item.body === 'Design material: ASTM A106 Grade B.')).toBe(
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

  it('skips non-submittable parameters that appear earlier in the list', () => {
    const parameter = getCurrentEditableParameter({
      ...mockTaskState,
      progress: {
        ...mockTaskState.progress,
        current_step_id: 'design_temperature',
        submittable_parameters: ['design_temperature'],
      },
      parameters: [
        {
          name: 'joint_category',
          label: 'Joint Category',
          type: 'dropdown',
          required: true,
          units: [],
          default_unit: 'dimensionless',
          default_value: 'seamless',
          value: 'seamless',
          options: [{ value: 'seamless', label: 'Seamless' }],
          validation: null,
          status: 'confirmation_required',
          requires_confirmation: true,
          submittable: false,
        },
        {
          name: 'design_temperature',
          label: 'Design Temperature',
          type: 'number',
          required: true,
          units: ['C'],
          default_unit: 'C',
          default_value: null,
          value: null,
          options: null,
          validation: null,
          status: 'pending',
          requires_confirmation: false,
          submittable: true,
        },
      ],
    })

    expect(parameter?.name).toBe('design_temperature')
  })
})
