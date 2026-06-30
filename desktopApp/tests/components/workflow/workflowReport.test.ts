import { describe, expect, it } from 'vitest'

import {
  completedStepStatement,
  parameterNextStepPrompt,
  USER_INPUT_STEP_PROMPT,
} from '@/components/workflow/workflowReport'

describe('workflowReport', () => {
  it('uses the shared prompt for user input steps', () => {
    expect(
      parameterNextStepPrompt({
        name: 'material',
        label: 'Material',
        type: 'material',
        required: true,
        units: [],
        default_unit: 'dimensionless',
        default_value: null,
        value: null,
        options: null,
        validation: null,
        status: 'pending',
        requires_confirmation: false,
      }),
    ).toBe(USER_INPUT_STEP_PROMPT)
  })

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

  it('formats the required wall thickness statement from the timeline value', () => {
    expect(
      completedStepStatement({
        id: 'thickness',
        title: 'Thickness',
        status: 'done',
        displayValue: '0.259 mm',
      }),
    ).toBe('Required wall thickness: 0.259 mm.')
  })

  it('does not emit statements for internal execution assumptions', () => {
    expect(
      completedStepStatement({
        id: 'd_input_mode',
        title: 'D Input Mode',
        status: 'done',
        displayValue: 'nps_lookup',
      }),
    ).toBeNull()
    expect(
      completedStepStatement({
        id: 'thin_wall',
        title: 'Thin Wall',
        status: 'done',
        displayValue: 'True',
      }),
    ).toBeNull()
  })
})
