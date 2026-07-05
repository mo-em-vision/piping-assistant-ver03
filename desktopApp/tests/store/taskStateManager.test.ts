import { describe, expect, it } from 'vitest'

import { isReportSectionVisible } from '@/store/taskStateManager'
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
