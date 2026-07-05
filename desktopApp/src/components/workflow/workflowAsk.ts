import type { TaskStateDto } from '@/types/backend/api'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

export const DEFAULT_WORKFLOW_ASK_PROMPT = 'Complete the fields below to continue.'

export type WorkflowAskKind = 'input' | 'clarify' | 'waiting' | 'none'

export interface WorkflowAsk {
  kind: WorkflowAskKind
  prompt: string | null
  parameter: ParameterDefinitionDto | null
}

type GoalRecord = {
  key?: string
  target_parameter?: string
  question?: { prompt?: string }
}

type ExecutionContextState = {
  state?: {
    blocked_goals?: string[]
  }
}

function parameterIsSubmittable(
  parameter: { name: string; submittable?: boolean },
  state: TaskStateDto,
): boolean {
  if (parameter.submittable != null) {
    return parameter.submittable
  }
  const submittable = state.progress.submittable_parameters
  if (submittable) {
    return submittable.includes(parameter.name)
  }
  return true
}

function blockedGoalIds(state: TaskStateDto): string[] {
  const ctx = state.execution_context as ExecutionContextState | undefined
  return ctx?.state?.blocked_goals ?? []
}

function goalPromptForParameter(state: TaskStateDto, parameterName: string): string | null {
  const goals = state.goals
  if (!goals) {
    return null
  }

  for (const goal of Object.values(goals) as GoalRecord[]) {
    const key = goal.key ?? goal.target_parameter
    if (key !== parameterName) {
      continue
    }
    const prompt = goal.question?.prompt?.trim()
    if (prompt) {
      return prompt
    }
  }
  return null
}

function blockedGoalPrompt(state: TaskStateDto): string | null {
  const goals = state.goals
  if (!goals) {
    return null
  }

  for (const goalId of blockedGoalIds(state)) {
    const goal = goals[goalId] as GoalRecord | undefined
    const prompt = goal?.question?.prompt?.trim()
    if (prompt) {
      return prompt
    }
  }
  return null
}

function firstSubmittableParameter(state: TaskStateDto): ParameterDefinitionDto | null {
  const submittableIds = state.progress.submittable_parameters ?? []
  if (submittableIds.length) {
    const fromSubmittable = state.parameters.find(
      (parameter) =>
        submittableIds.includes(parameter.name) &&
        parameterIsSubmittable(parameter, state) &&
        (parameter.status === 'pending' || parameter.status === 'confirmation_required'),
    )
    if (fromSubmittable) {
      return fromSubmittable
    }
  }

  const activeStepId = state.progress.current_step_id
  if (activeStepId) {
    const fromActiveStep = state.parameters.find(
      (parameter) =>
        parameter.name === activeStepId &&
        parameterIsSubmittable(parameter, state) &&
        parameter.status !== 'confirmed',
    )
    if (fromActiveStep) {
      return fromActiveStep
    }
  }

  return (
    state.parameters.find(
      (parameter) =>
        parameterIsSubmittable(parameter, state) &&
        (parameter.status === 'pending' || parameter.status === 'confirmation_required'),
    ) ?? null
  )
}

export function getCurrentEditableParameter(state: TaskStateDto | null): ParameterDefinitionDto | null {
  if (!state?.parameters?.length) {
    return null
  }

  const editing = state.parameters.find((parameter) => parameter.editing)
  if (editing) {
    return editing
  }

  const editSession = state.outputs?.edit_session as { parameter?: string } | undefined
  if (editSession?.parameter) {
    return state.parameters.find((parameter) => parameter.name === editSession.parameter) ?? null
  }

  return firstSubmittableParameter(state)
}

function promptForParameter(
  parameter: ParameterDefinitionDto,
  timeline: TimelineStepViewModel[],
  state: TaskStateDto,
): string {
  const guidance = parameter.guidance?.trim()
  if (guidance) {
    return guidance
  }

  const timelineStep =
    timeline.find((step) => step.id === parameter.name && step.status === 'active') ??
    timeline.find((step) => step.status === 'active')
  const hint = timelineStep?.hint?.trim()
  if (hint) {
    return hint
  }

  const goalPrompt = goalPromptForParameter(state, parameter.name)
  if (goalPrompt) {
    return goalPrompt
  }

  return DEFAULT_WORKFLOW_ASK_PROMPT
}

function activeTimelineStep(timeline: TimelineStepViewModel[]): TimelineStepViewModel | null {
  return timeline.find((step) => step.status === 'active') ?? null
}

export function getWorkflowAsk(
  state: TaskStateDto | null,
  timeline: TimelineStepViewModel[] = [],
): WorkflowAsk {
  if (!state) {
    return { kind: 'none', prompt: null, parameter: null }
  }

  const backendAsk = state.current_ask
  if (backendAsk?.kind === 'input' && backendAsk.parameter_id) {
    const parameter =
      state.parameters.find((item) => item.name === backendAsk.parameter_id) ??
      getCurrentEditableParameter(state)
    if (parameter) {
      return {
        kind: 'input',
        prompt:
          backendAsk.prompt?.trim() ||
          parameter.guidance?.trim() ||
          promptForParameter(parameter, timeline, state),
        parameter,
      }
    }
  }

  if (backendAsk?.kind === 'clarify') {
    return {
      kind: 'clarify',
      prompt: backendAsk.prompt?.trim() ?? blockedGoalPrompt(state) ?? 'Workflow path is blocked.',
      parameter: null,
    }
  }

  if (backendAsk?.kind === 'waiting') {
    const activeStep = activeTimelineStep(timeline)
    return {
      kind: 'waiting',
      prompt:
        backendAsk.prompt?.trim() ??
        activeStep?.hint?.trim() ??
        (activeStep?.title ? `Working on ${activeStep.title}…` : DEFAULT_WORKFLOW_ASK_PROMPT),
      parameter: null,
    }
  }

  const parameter = getCurrentEditableParameter(state)
  if (parameter) {
    return {
      kind: 'input',
      prompt: promptForParameter(parameter, timeline, state),
      parameter,
    }
  }

  const blocked = blockedGoalIds(state)
  if (blocked.length > 0) {
    return {
      kind: 'clarify',
      prompt: blockedGoalPrompt(state) ?? 'Workflow path is blocked.',
      parameter: null,
    }
  }

  const activeStep = activeTimelineStep(timeline)
  if (activeStep) {
    const prompt =
      activeStep.hint?.trim() ??
      (activeStep.title ? `Working on ${activeStep.title}…` : DEFAULT_WORKFLOW_ASK_PROMPT)
    return {
      kind: 'waiting',
      prompt,
      parameter: null,
    }
  }

  return { kind: 'none', prompt: null, parameter: null }
}
