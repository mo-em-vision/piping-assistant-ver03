import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

export type WorkflowHistoryItem = {
  id: string
  kind: 'output'
  block: DisplayOutputBlock
}

export function buildWorkflowHistory(
  _timeline: TimelineStepViewModel[],
  displayOutputs: DisplayOutputBlock[],
): WorkflowHistoryItem[] {
  return displayOutputs.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output',
    block,
  }))
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

const NON_INPUT_ACTIVE_STEPS = new Set(['report', 'thickness'])

function firstEditableParameter(state: TaskStateDto) {
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
  if (activeStepId && !NON_INPUT_ACTIVE_STEPS.has(activeStepId)) {
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

export function getCurrentEditableParameter(state: TaskStateDto | null) {
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

  return firstEditableParameter(state)
}
