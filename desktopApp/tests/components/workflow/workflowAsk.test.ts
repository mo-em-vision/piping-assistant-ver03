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
      viewModel!.timeline.map((step) =>
        step.id === 'thickness'
          ? {
              ...step,
              status: 'active',
              hint: 'Computing required wall thickness from the confirmed inputs.',
            }
          : step,
      ),
    )

    expect(ask.kind).toBe('waiting')
    expect(ask.prompt).toBe('Computing required wall thickness from the confirmed inputs.')
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
})
