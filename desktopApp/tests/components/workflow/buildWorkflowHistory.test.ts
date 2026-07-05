import { describe, expect, it } from 'vitest'

import { applyOptimisticParameterSubmit } from '@/components/workflow/optimisticWorkflowTransition'
import {
  buildWorkflowHistory,
  getCurrentEditableParameter,
} from '@/components/workflow/buildWorkflowHistory'
import { mockTaskState } from '@/mock/taskState.mock'
import { buildTaskStateViewModel } from '@/store/taskStateManager'

describe('buildWorkflowHistory', () => {
  it('maps display outputs to workflow history items', () => {
    const viewModel = buildTaskStateViewModel(mockTaskState)
    expect(viewModel).not.toBeNull()

    const items = buildWorkflowHistory(viewModel!.timeline, mockTaskState.display_outputs)

    expect(items.every((item) => item.kind === 'output')).toBe(true)
    expect(items.some((item) => item.kind === 'output' && item.block.id === 'preview-equation')).toBe(
      true,
    )
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

  it('prefers submittable parameters from the backend list', () => {
    const parameter = getCurrentEditableParameter({
      ...mockTaskState,
      progress: {
        ...mockTaskState.progress,
        current_step_id: 'report',
        submittable_parameters: ['corrosion_allowance'],
      },
      parameters: [
        {
          name: 'corrosion_allowance',
          label: 'Corrosion allowance',
          type: 'number',
          required: true,
          units: ['mm'],
          default_unit: 'mm',
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

    expect(parameter?.name).toBe('corrosion_allowance')
  })

  it('returns the next timeline parameter after optimistic submit when it exists in parameters', () => {
    const state = applyOptimisticParameterSubmit(
      {
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
              id: 'outside_diameter',
              title: 'Outside Diameter',
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
          current_step_id: 'outside_diameter',
          missing_inputs: ['outside_diameter', 'material'],
          missing_assumptions: [],
          submittable_parameters: ['outside_diameter'],
          step_progress: [],
        },
        inputs: {},
        outputs: {},
        warnings: [],
        parameters: [
          {
            name: 'outside_diameter',
            label: 'Outside Diameter',
            type: 'number',
            required: true,
            units: ['in'],
            default_unit: 'in',
            default_value: null,
            value: null,
            options: null,
            validation: null,
            status: 'pending',
            requires_confirmation: false,
          },
          {
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
          },
        ],
        display_outputs: [],
        active_node_context: null,
        options: { available_workflows: [] },
        errors: [],
      },
      'outside_diameter',
      4.5,
      'in',
    )

    const parameter = getCurrentEditableParameter(state)

    expect(parameter?.name).toBe('material')
    expect(parameter?.type).toBe('material')
    expect(parameter?.status).toBe('pending')
  })
})
