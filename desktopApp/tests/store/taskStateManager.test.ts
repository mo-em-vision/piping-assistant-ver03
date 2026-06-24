import { describe, expect, it } from 'vitest'

import { isReportSectionVisible } from '@/store/taskStateManager'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

function timelineWithReportStatus(status: TimelineStepViewModel['status']): TimelineStepViewModel[] {
  return [
    { id: 'material', title: 'Material', status: 'done', displayValue: 'ASTM A106 Grade B', hint: null, editable: false },
    { id: 'thickness', title: 'Thickness', status: 'done', displayValue: '12.5 mm', hint: null, editable: false },
    { id: 'report', title: 'Report', status, displayValue: null, hint: null, editable: false },
  ]
}

describe('isReportSectionVisible', () => {
  it('returns false while the report step is pending', () => {
    expect(isReportSectionVisible(timelineWithReportStatus('pending'))).toBe(false)
  })

  it('returns true when the report step is active or done', () => {
    expect(isReportSectionVisible(timelineWithReportStatus('active'))).toBe(true)
    expect(isReportSectionVisible(timelineWithReportStatus('done'))).toBe(true)
  })
})
