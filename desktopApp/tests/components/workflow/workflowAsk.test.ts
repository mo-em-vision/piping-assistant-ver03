import { describe, expect, it } from 'vitest'

import { getWorkflowAsk } from '@/components/workflow/workflowAsk'
import { mockTaskState } from '@/mock/taskState.mock'
import { buildTaskStateViewModel } from '@/store/taskStateManager'

describe('getWorkflowAsk', () => {
  it('uses parameter guidance for the current submittable input', () => {
    const viewModel = buildTaskStateViewModel(mockTaskState)
    expect(viewModel).not.toBeNull()

    const ask = getWorkflowAsk(
      {
        ...mockTaskState,
        parameters: mockTaskState.parameters.map((parameter) =>
          parameter.name === 'nominal_pipe_size'
            ? {
                ...parameter,
                guidance: 'Enter the nominal pipe size for the straight section.',
              }
            : parameter,
        ),
      },
      viewModel!.timeline,
    )

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('nominal_pipe_size')
    expect(ask.prompt).toBe('Enter the nominal pipe size for the straight section.')
  })

  it('returns a clarify ask when goals are blocked and no input is submittable', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      parameters: [],
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: [],
      },
      execution_context: {
        state: {
          blocked_goals: ['goal-1'],
        },
      },
      goals: {
        'goal-1': {
          key: 'straight_pipe_section',
          question: {
            prompt: 'Non-straight pipe sections are not supported for this workflow.',
          },
        },
      },
    })

    expect(ask.kind).toBe('clarify')
    expect(ask.parameter).toBeNull()
    expect(ask.prompt).toBe('Non-straight pipe sections are not supported for this workflow.')
  })

  it('returns a waiting ask from the active timeline step hint', () => {
    const viewModel = buildTaskStateViewModel(mockTaskState)
    expect(viewModel).not.toBeNull()

    const ask = getWorkflowAsk(
      {
        ...mockTaskState,
        parameters: [],
        progress: {
          ...mockTaskState.progress,
          submittable_parameters: [],
          current_step_id: 'thickness',
        },
      },
      viewModel!.timeline.map((step) => {
        if (step.id === 'thickness') {
          return {
            ...step,
            status: 'active',
            hint: 'Computing required wall thickness from the confirmed inputs.',
          }
        }
        if (step.id === 'nominal_pipe_size' && step.status === 'active') {
          return { ...step, status: 'done' }
        }
        return step
      }),
    )

    expect(ask.kind).toBe('waiting')
    expect(ask.prompt).toBe('Computing required wall thickness from the confirmed inputs.')
  })

  it('resolves material_grade current_ask against backend material_grade parameter', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      current_ask: {
        kind: 'input',
        parameter_id: 'material_grade',
        prompt: 'Select the pipe material. (start typing to see the available options)',
      },
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['material_grade'],
        current_step_id: 'material_grade',
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
      ],
      execution_context: {
        state: {
          blocked_goals: ['verify-engineering-goal'],
        },
      },
      goals: {
        'verify-engineering-goal': {
          key: 'verify-engineering-goal',
        },
      },
    })

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('material_grade')
    expect(ask.prompt).toBe('Select the pipe material. (start typing to see the available options)')
  })

  it('prefers backend current_ask when provided', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      current_ask: {
        kind: 'input',
        parameter_id: 'nominal_pipe_size',
        prompt: 'Backend-authored pipe size question.',
      },
      parameters: mockTaskState.parameters.map((parameter) =>
        parameter.name === 'nominal_pipe_size'
          ? { ...parameter, guidance: 'Ignored when current_ask is set.' }
          : parameter,
      ),
    })

    expect(ask.kind).toBe('input')
    expect(ask.prompt).toBe('Backend-authored pipe size question.')
    expect(ask.parameter?.name).toBe('nominal_pipe_size')
  })

  it('ignores stale backend current_ask prompt when the active parameter changed', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      current_ask: {
        kind: 'input',
        parameter_id: 'material_grade',
        prompt: 'Select the pipe material. (start typing to see the available options)',
      },
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['design_temperature'],
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
          value: 'SA-106 B',
          options: null,
          validation: null,
          status: 'confirmed',
          requires_confirmation: false,
          submittable: false,
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
          submittable: true,
          guidance:
            'Please provide the design temperature because allowable stress depends on metal temperature.',
        },
      ],
    })

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('design_temperature')
    expect(ask.prompt).toBe(
      'Please provide the design temperature because allowable stress depends on metal temperature.',
    )
  })

  it('returns an input ask when the active timeline step has a pending parameter but backend waiting', () => {
    const ask = getWorkflowAsk(
      {
        ...mockTaskState,
        current_ask: {
          kind: 'waiting',
          parameter_id: null,
          prompt: null,
        },
        progress: {
          ...mockTaskState.progress,
          submittable_parameters: [],
          current_step_id: 'corrosion_allowance',
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
            submittable: false,
            guidance:
              'For c (mechanical allowances): the default is 0.5 mm when machined surfaces or grooves where tolerance is not specified. Confirm or enter another value.',
          },
        ],
      },
      [
        {
          id: 'corrosion_allowance',
          title: 'Corrosion allowance',
          status: 'active',
          value: null,
          unit: null,
        },
      ],
    )

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('corrosion_allowance')
    expect(ask.prompt).toContain('0.5 mm')
  })
})
