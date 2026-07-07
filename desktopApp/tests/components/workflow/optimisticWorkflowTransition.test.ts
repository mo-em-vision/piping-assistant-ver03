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
          id: 'internal_design_gage_pressure',
          title: 'Design Pressure',
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
      submittable_parameters: ['pressure_loading'],
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
      {
        name: 'internal_design_gage_pressure',
        label: 'Design Pressure',
        type: 'number',
        required: true,
        units: ['bar'],
        default_unit: 'bar',
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
  }
}

function materialHandoffState(): TaskStateDto {
  return {
    ...pipeWallState(),
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
          id: 'material_grade',
          title: 'Material Grade',
          status: 'pending',
          value: null,
          unit: null,
        },
      ],
      steps: [],
      completed_count: 0,
      total_count: 2,
      current_step_id: 'outside_diameter',
      missing_inputs: ['outside_diameter', 'material_grade'],
      missing_assumptions: [],
      submittable_parameters: ['outside_diameter'],
      step_progress: [],
    },
    parameters: [
      {
        name: 'outside_diameter',
        label: 'Outside Diameter',
        type: 'number',
        required: true,
        units: ['in', 'mm'],
        default_unit: 'in',
        default_value: null,
        value: null,
        options: null,
        validation: null,
        status: 'pending',
        requires_confirmation: false,
      },
      {
        name: 'material_grade',
        label: 'Material Grade',
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
  }
}

function materialToTemperatureHandoffState(): TaskStateDto {
  return {
    ...materialHandoffState(),
    current_ask: {
      kind: 'input',
      parameter_id: 'material_grade',
      prompt: 'Select the pipe material. (start typing to see the available options)',
    },
    progress: {
      timeline: [
        {
          id: 'material_grade',
          title: 'Material Grade',
          status: 'active',
          value: null,
          unit: null,
        },
        {
          id: 'design_temperature',
          title: 'Design Temperature',
          status: 'pending',
          value: null,
          unit: null,
        },
      ],
      steps: [],
      completed_count: 0,
      total_count: 2,
      current_step_id: 'material_grade',
      missing_inputs: ['material_grade', 'design_temperature'],
      missing_assumptions: [],
      submittable_parameters: ['material_grade'],
      step_progress: [],
    },
    parameters: [
      {
        name: 'material_grade',
        label: 'Material Grade',
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
        submittable: true,
        guidance: 'Select the pipe material. (start typing to see the available options)',
      },
      {
        name: 'design_temperature',
        label: 'Design Temperature',
        type: 'number',
        required: true,
        units: ['C', 'F'],
        default_unit: 'C',
        default_value: null,
        value: null,
        options: null,
        validation: null,
        status: 'pending',
        requires_confirmation: false,
        guidance:
          'Please provide the design temperature because allowable stress depends on metal temperature.',
      },
    ],
  }
}

describe('applyOptimisticParameterSubmit', () => {
  it('marks the submitted parameter confirmed and advances to the next phased step', () => {
    const next = applyOptimisticParameterSubmit(
      pipeWallState(),
      'pressure_loading',
      'internal_pressure',
    )

    expect(next.parameters.find((item) => item.name === 'pressure_loading')?.status).toBe('confirmed')
    expect(next.parameters.find((item) => item.name === 'internal_design_gage_pressure')?.status).toBe('pending')
    expect(next.progress.current_step_id).toBe('internal_design_gage_pressure')
    expect(next.progress.submittable_parameters).toEqual(['internal_design_gage_pressure'])
    expect(next.progress.timeline.find((step) => step.id === 'internal_design_gage_pressure')?.status).toBe('active')
  })

  it('advances from outside diameter to material with submittable parameters updated', () => {
    const next = applyOptimisticParameterSubmit(materialHandoffState(), 'outside_diameter', 4.5, 'in')

    expect(next.parameters.find((item) => item.name === 'outside_diameter')?.status).toBe('confirmed')
    expect(next.parameters.find((item) => item.name === 'material_grade')?.status).toBe('pending')
    expect(next.progress.current_step_id).toBe('material_grade')
    expect(next.progress.submittable_parameters).toEqual(['material_grade'])
    expect(next.progress.timeline.find((step) => step.id === 'material_grade')?.status).toBe('active')
  })

  it('updates current_ask when advancing from material to design temperature', () => {
    const next = applyOptimisticParameterSubmit(
      materialToTemperatureHandoffState(),
      'material_grade',
      'SA-106 B',
      undefined,
      'SA-106 B',
    )

    expect(next.parameters.find((item) => item.name === 'material_grade')?.status).toBe('confirmed')
    expect(next.parameters.find((item) => item.name === 'design_temperature')?.status).toBe('pending')
    expect(next.progress.current_step_id).toBe('design_temperature')
    expect(next.progress.submittable_parameters).toEqual(['design_temperature'])
    expect(next.current_ask).toEqual({
      kind: 'input',
      parameter_id: 'design_temperature',
      prompt:
        'Please provide the design temperature because allowable stress depends on metal temperature.',
    })
  })
})
