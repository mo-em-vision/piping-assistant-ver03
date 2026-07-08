import { describe, expect, it } from 'vitest'

import { DEFAULT_WORKFLOW_ASK_PROMPT, getWorkflowAsk } from '@/components/workflow/workflowAsk'
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

  it('reflects only the current submittable parameter', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['design_temperature'],
        missing_inputs: ['design_temperature', 'corrosion_allowance'],
      },
      parameters: [
        {
          name: 'nominal_pipe_size',
          label: 'Nominal Pipe Size',
          type: 'dropdown',
          required: true,
          units: [],
          default_unit: 'dimensionless',
          default_value: '4',
          value: '4',
          options: [{ value: '4', label: 'NPS 4' }],
          validation: null,
          status: 'confirmed',
          requires_confirmation: false,
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
          guidance: 'Enter design temperature.',
        },
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
        },
      ],
    })

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('design_temperature')
    expect(ask.parameter?.name).not.toBe('corrosion_allowance')
  })

  it('resolves prompt from parameter guidance without legacy_goal_map', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      legacy_goal_map: undefined,
      goals: undefined,
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['design_temperature'],
      },
      parameters: [
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
          guidance: 'Enter design temperature for allowable stress lookup.',
        },
      ],
    })

    expect(ask.kind).toBe('input')
    expect(ask.prompt).toBe('Enter design temperature for allowable stress lookup.')
  })

  it('resolves prompt from current_ask without legacy_goal_map', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      legacy_goal_map: undefined,
      goals: undefined,
      current_ask: {
        kind: 'input',
        parameter_id: 'nominal_pipe_size',
        prompt: 'Backend current_ask prompt for pipe size.',
      },
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['nominal_pipe_size'],
      },
      parameters: mockTaskState.parameters.map((parameter) =>
        parameter.name === 'nominal_pipe_size'
          ? { ...parameter, status: 'pending', submittable: true }
          : parameter,
      ),
    })

    expect(ask.kind).toBe('input')
    expect(ask.prompt).toBe('Backend current_ask prompt for pipe size.')
  })

  it('resolves prompt from flow_guidance active_prompt without legacy_goal_map', () => {
    const ask = getWorkflowAsk(
      {
        ...mockTaskState,
        legacy_goal_map: undefined,
        goals: undefined,
        current_ask: {
          kind: 'waiting',
          parameter_id: null,
          prompt: null,
        },
        flow_guidance: {
          presentation_blocks: [],
          transcript_blocks: [],
          active_prompt: {
            block_id: 'prompt-corrosion',
            kind: 'prompt',
            source: 'messaging',
            text: 'Confirm corrosion allowance from flow guidance.',
            payload: { parameter_id: 'corrosion_allowance' },
          },
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
    expect(ask.prompt).toBe('Confirm corrosion allowance from flow guidance.')
  })

  it('prefers short_prompt over full prompt for composer display', () => {
    const ask = getWorkflowAsk({
      ...mockTaskState,
      current_ask: {
        kind: 'input',
        parameter_id: 'internal_design_gage_pressure',
        prompt:
          'Enter the internal design gage pressure P, including units. Examples: 500 psi, 8 bar.',
        short_prompt: 'Enter internal design gage pressure P.',
      },
      parameters: [
        {
          name: 'internal_design_gage_pressure',
          label: 'Internal design gage pressure',
          type: 'unit',
          required: true,
          units: ['bar', 'psi'],
          default_unit: 'bar',
          default_value: null,
          value: null,
          options: null,
          validation: null,
          status: 'pending',
          requires_confirmation: false,
          submittable: true,
        },
      ],
      progress: {
        ...mockTaskState.progress,
        submittable_parameters: ['internal_design_gage_pressure'],
        current_step_id: 'internal_design_gage_pressure',
      },
    })

    expect(ask.prompt).toBe('Enter internal design gage pressure P.')
    expect(ask.prompt).not.toContain('500 psi')
  })

  it('does not fall back to DEFAULT_WORKFLOW_ASK_PROMPT for active input with parameter_id', () => {
    const ask = getWorkflowAsk(
      {
        ...mockTaskState,
        current_ask: {
          kind: 'input',
          parameter_id: 'internal_design_gage_pressure',
          prompt:
            'Enter the internal design gage pressure P, including units. Examples: 500 psi, 8 bar.',
        },
        parameters: [
          {
            name: 'internal_design_gage_pressure',
            label: 'Internal design gage pressure',
            type: 'unit',
            required: true,
            units: ['bar', 'psi'],
            default_unit: 'bar',
            default_value: null,
            value: null,
            options: null,
            validation: null,
            status: 'pending',
            requires_confirmation: false,
            submittable: true,
          },
        ],
        progress: {
          ...mockTaskState.progress,
          submittable_parameters: ['internal_design_gage_pressure'],
          current_step_id: 'internal_design_gage_pressure',
        },
      },
      [],
    )

    expect(ask.kind).toBe('input')
    expect(ask.parameter?.name).toBe('internal_design_gage_pressure')
    expect(ask.prompt).not.toBe(DEFAULT_WORKFLOW_ASK_PROMPT)
    expect(ask.prompt).toBeTruthy()
    expect(ask.prompt).toContain('500 psi')
  })
})
