import { describe, expect, it } from 'vitest'

import { applyOptimisticParameterSubmit } from '@/components/workflow/optimisticWorkflowTransition'
import type { TaskStateDto } from '@/types/backend/api'

function pipeWallState(): TaskStateDto {
  return {
    task_id: 'test-task',
    name: 'Pipe Thickness Calculation',
    workflow_id: 'pipe_wall_thickness_design',
    discipline: 'Piping',
    description: 'test',
    status: 'awaiting_input',
    active_nodes: [],
    progress: {
      timeline: [
        {
          id: 'pressure_loading',
          title: 'Pressure loading',
          status: 'active',
          value: null,
          unit: null,
        },
        {
          id: 'material',
          title: 'Material',
          status: 'pending',
          value: null,
          unit: null,
        },
      ],
      steps: [],
      completed_count: 0,
      total_count: 2,
      current_step_id: 'pressure_loading',
      missing_inputs: [],
      missing_assumptions: [],
      step_progress: [],
    },
    inputs: {},
    outputs: {},
    warnings: [],
    parameters: [
      {
        name: 'pressure_loading',
        label: 'Pressure Loading',
        type: 'dropdown',
        required: true,
        units: [],
        default_unit: 'dimensionless',
        default_value: null,
        value: null,
        options: [
          { value: 'internal_pressure', label: 'Internal Pressure' },
          { value: 'external_pressure', label: 'External Pressure' },
        ],
        validation: null,
        status: 'pending',
        requires_confirmation: false,
      },
    ],
    display_outputs: [],
    active_node_context: null,
    options: { available_workflows: [] },
    errors: [],
  }
}

describe('applyOptimisticParameterSubmit', () => {
  it('marks the submitted parameter confirmed and advances timeline when the next step exists', () => {
    const next = applyOptimisticParameterSubmit(
      pipeWallState(),
      'pressure_loading',
      'internal_pressure',
    )

    expect(next.parameters.find((item) => item.name === 'material')).toBeUndefined()
    expect(next.parameters.find((item) => item.name === 'pressure_loading')?.status).toBe('confirmed')
    expect(next.progress.current_step_id).toBe('material')
    expect(next.progress.timeline.find((step) => step.id === 'material')?.status).toBe('active')
  })
})
