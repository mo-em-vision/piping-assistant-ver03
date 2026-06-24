import { describe, expect, it } from 'vitest'

import { completedStepStatement } from '@/components/workflow/workflowReport'

describe('workflowReport', () => {
  it('does not emit a separate statement for joint category', () => {
    expect(
      completedStepStatement({
        id: 'joint_category',
        title: 'Joint category',
        status: 'done',
        displayValue: 'seamless',
      }),
    ).toBeNull()
  })
})
