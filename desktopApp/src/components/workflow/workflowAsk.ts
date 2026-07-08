import type { TaskStateDto } from '@/types/backend/api'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

export const DEFAULT_WORKFLOW_ASK_PROMPT = 'Complete the fields below to continue.'

const MATERIAL_PARAMETER_NAMES = new Set(['material', 'material_grade'])

export function parameterNamesMatch(askId: string, parameterName: string): boolean {
  if (askId === parameterName) {
    return true
  }
  return MATERIAL_PARAMETER_NAMES.has(askId) && MATERIAL_PARAMETER_NAMES.has(parameterName)
}

export function findParameterForStepId(
  parameters: ParameterDefinitionDto[],
  stepId: string,
): ParameterDefinitionDto | undefined {
  return parameters.find((parameter) => parameterNamesMatch(stepId, parameter.name))
}

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
    return submittable.some((id) => parameterNamesMatch(id, parameter.name))
  }
  return true
}

function blockedGoalIds(state: TaskStateDto): string[] {
  const ctx = state.execution_context as ExecutionContextState | undefined
  return ctx?.state?.blocked_goals ?? []
}

function goalMapFromState(state: TaskStateDto): Record<string, GoalRecord> | null {
  const map = state.legacy_goal_map ?? state.goals
  if (!map) {
    return null
  }
  return map as Record<string, GoalRecord>
}

type FlowGuidancePromptBlock = {
  text?: string | null
  payload?: { parameter_id?: string | null }
  refs?: { parameter_id?: string | null }
}

function flowGuidancePromptForParameter(state: TaskStateDto, parameterName: string): string | null {
  const flowGuidance = (state as TaskStateDto & { flow_guidance?: { active_prompt?: FlowGuidancePromptBlock } })
    .flow_guidance
  const activePrompt = flowGuidance?.active_prompt
  if (!activePrompt?.text?.trim()) {
    return null
  }
  const promptParameterId =
    activePrompt.payload?.parameter_id?.trim() ||
    activePrompt.refs?.parameter_id?.trim() ||
    null
  if (promptParameterId && !parameterNamesMatch(promptParameterId, parameterName)) {
    return null
  }
  return activePrompt.text.trim()
}

function goalPromptForParameter(state: TaskStateDto, parameterName: string): string | null {
  const goals = goalMapFromState(state)
  if (!goals) {
    return null
  }

  for (const goal of Object.values(goals)) {
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
  const goals = goalMapFromState(state)
  if (!goals) {
    return null
  }

  for (const goalId of blockedGoalIds(state)) {
    const goal = goals[goalId]
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
        submittableIds.some((id) => parameterNamesMatch(id, parameter.name)) &&
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

function resolveInputAskParameter(
  state: TaskStateDto,
  backendParameterId?: string | null,
): ParameterDefinitionDto | null {
  const editable = getCurrentEditableParameter(state)
  if (!backendParameterId) {
    return editable
  }

  const backendTarget = state.parameters.find((parameter) =>
    parameterNamesMatch(backendParameterId, parameter.name),
  )
  if (
    backendTarget &&
    parameterIsSubmittable(backendTarget, state) &&
    (backendTarget.status === 'pending' || backendTarget.status === 'confirmation_required')
  ) {
    return backendTarget
  }

  return editable
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

  const flowGuidancePrompt = flowGuidancePromptForParameter(state, parameter.name)
  if (flowGuidancePrompt) {
    return flowGuidancePrompt
  }

  const goalPrompt = goalPromptForParameter(state, parameter.name)
  if (goalPrompt) {
    return goalPrompt
  }

  return DEFAULT_WORKFLOW_ASK_PROMPT
}

const NON_INPUT_TIMELINE_STEP_IDS = new Set(['thickness', 'report'])

function activeTimelineStep(timeline: TimelineStepViewModel[]): TimelineStepViewModel | null {
  return timeline.find((step) => step.status === 'active') ?? null
}

function parameterForActiveTimelineStep(
  state: TaskStateDto,
  timeline: TimelineStepViewModel[],
): ParameterDefinitionDto | null {
  const activeStep = activeTimelineStep(timeline)
  if (!activeStep || NON_INPUT_TIMELINE_STEP_IDS.has(activeStep.id)) {
    return null
  }

  const parameter = state.parameters.find((item) =>
    parameterNamesMatch(activeStep.id, item.name),
  )
  if (!parameter || parameter.status === 'confirmed') {
    return null
  }
  if (parameter.status === 'pending' || parameter.status === 'confirmation_required') {
    return parameter
  }
  return null
}

export function getWorkflowAsk(
  state: TaskStateDto | null,
  timeline: TimelineStepViewModel[] = [],
): WorkflowAsk {
  if (!state) {
    return { kind: 'none', prompt: null, parameter: null }
  }

  const backendAsk = state.current_ask
  if (backendAsk?.kind === 'input') {
    const parameter = resolveInputAskParameter(state, backendAsk.parameter_id)
    if (parameter) {
      const promptMatchesParameter =
        backendAsk.parameter_id != null &&
        parameterNamesMatch(backendAsk.parameter_id, parameter.name)
      return {
        kind: 'input',
        prompt:
          (promptMatchesParameter ? backendAsk.prompt?.trim() : null) ||
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
    const activeParameter = parameterForActiveTimelineStep(state, timeline)
    if (activeParameter) {
      return {
        kind: 'input',
        prompt: promptForParameter(activeParameter, timeline, state),
        parameter: activeParameter,
      }
    }
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
  const activeParameter = parameterForActiveTimelineStep(state, timeline)
  if (activeParameter) {
    return {
      kind: 'input',
      prompt: promptForParameter(activeParameter, timeline, state),
      parameter: activeParameter,
    }
  }
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
