import { findParameterForStepId } from '@/components/workflow/workflowAsk'
import type { TaskStateDto } from '@/types/backend/api'
import { formatEngineeringDisplayValue } from '@/utils/engineeringDisplay'

function formatDisplayValue(value: unknown, unit?: string): string {
  return formatEngineeringDisplayValue(value, unit)
}

function findNextTimelineStepId(
  timeline: TaskStateDto['progress']['timeline'],
  parameter: string,
): string | null {
  const parameterIndex = timeline.findIndex((step) => step.id === parameter)
  if (parameterIndex >= 0) {
    for (let index = parameterIndex + 1; index < timeline.length; index += 1) {
      if (timeline[index].status !== 'done') {
        return timeline[index].id
      }
    }
    return null
  }

  return timeline.find((step) => step.status === 'pending')?.id ?? null
}

function advanceTimeline(
  timeline: TaskStateDto['progress']['timeline'],
  parameter: string,
  nextStepId: string | null,
  displayValue: string,
  value: unknown,
  unit?: string,
) {
  let activeAssigned = false

  return timeline.map((step) => {
    if (step.id === parameter) {
      return {
        ...step,
        status: 'done' as const,
        value,
        unit: unit ?? step.unit ?? null,
        display_value: displayValue,
      }
    }

    if (nextStepId && step.id === nextStepId && !activeAssigned) {
      activeAssigned = true
      return {
        ...step,
        status: 'active' as const,
        display_value: null,
        hint: step.hint ?? null,
      }
    }

    if (step.status === 'active' && step.id !== nextStepId) {
      return { ...step, status: 'pending' as const }
    }

    return step
  })
}

function canOptimisticallyActivateStep(state: TaskStateDto, stepId: string): boolean {
  return (
    state.parameters.some((parameter) => parameter.name === stepId) ||
    state.progress.timeline.some((step) => step.id === stepId)
  )
}

export function applyOptimisticParameterSubmit(
  state: TaskStateDto,
  parameter: string,
  value: unknown,
  unit?: string,
  displayValueOverride?: string,
): TaskStateDto {
  const displayValue = displayValueOverride ?? formatDisplayValue(value, unit)
  const candidateNextStepId = findNextTimelineStepId(state.progress.timeline, parameter)
  const nextStepId =
    candidateNextStepId != null && canOptimisticallyActivateStep(state, candidateNextStepId)
      ? candidateNextStepId
      : null

  const parameters = state.parameters.map((item) => {
    if (item.name === parameter) {
      return { ...item, value, status: 'confirmed' as const }
    }
    if (nextStepId && item.name === nextStepId && item.status !== 'confirmed') {
      return { ...item, status: 'pending' as const, submittable: true }
    }
    return item
  })

  const timeline = advanceTimeline(
    state.progress.timeline,
    parameter,
    nextStepId,
    displayValue,
    value,
    unit,
  )

  const nextParameter = nextStepId ? findParameterForStepId(parameters, nextStepId) : undefined
  const currentAsk =
    nextParameter != null
      ? {
          kind: 'input' as const,
          parameter_id: nextParameter.name,
          prompt: nextParameter.guidance?.trim() ?? null,
        }
      : nextStepId != null
        ? {
            kind: 'waiting' as const,
            parameter_id: null,
            prompt: null,
          }
        : state.current_ask

  return {
    ...state,
    current_ask: currentAsk,
    parameters,
    facts: {
      ...state.facts,
      [parameter]: {
        input_id: parameter,
        value,
        unit: unit ?? 'dimensionless',
        display_value: displayValue,
      },
    },
    progress: {
      ...state.progress,
      timeline,
      steps: timeline,
      current_step_id: nextStepId ?? state.progress.current_step_id,
      missing_inputs: state.progress.missing_inputs.filter((item) => item !== parameter),
      submittable_parameters: nextStepId ? [nextStepId] : state.progress.submittable_parameters,
    },
  }
}
