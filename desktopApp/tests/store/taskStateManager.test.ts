import { describe, expect, it } from 'vitest'

import { buildTaskStateViewModel, isReportSectionVisible } from '@/store/taskStateManager'
import { mockTaskState } from '@/mock/taskState.mock'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

function timelineWithReportHint(status: TimelineStepViewModel['status']): TimelineStepViewModel[] {
  return [
    {
      id: 'calculation',
      title: 'Thickness',
      status: 'done',
      displayValue: '1 mm',
      hint: null,
      editable: false,
    },
    {
      id: 'report-step',
      title: 'Report',
      status,
      displayValue: null,
      hint: 'Generate the engineering report',
      editable: false,
    },
  ]
}

describe('isReportSectionVisible', () => {
  it('is hidden when the report step is still pending', () => {
    expect(isReportSectionVisible(timelineWithReportHint('pending'))).toBe(false)
  })

  it('is visible when the report step is active or done', () => {
    expect(isReportSectionVisible(timelineWithReportHint('active'))).toBe(true)
    expect(isReportSectionVisible(timelineWithReportHint('done'))).toBe(true)
  })

  it('is visible when the task is completed', () => {
    expect(isReportSectionVisible([], { status: 'completed' } as never)).toBe(true)
  })
})

describe('task state missing inputs', () => {
  it('reflects only the current phase missing inputs from backend state', () => {
    const state = {
      ...mockTaskState,
      progress: {
        ...mockTaskState.progress,
        current_step_id: 'design_temperature',
        missing_inputs: ['design_temperature'],
        submittable_parameters: ['design_temperature'],
      },
    }

    const viewModel = buildTaskStateViewModel(state)

    expect(state.progress.missing_inputs).toEqual(['design_temperature'])
    expect(state.progress.missing_inputs).not.toContain('nominal_pipe_size')
    expect(viewModel?.currentStepId).toBe('design_temperature')
  })
})
