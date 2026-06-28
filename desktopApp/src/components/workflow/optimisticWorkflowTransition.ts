import type { TaskStateDto } from '@/types/backend/api'
import { formatEngineeringDisplayValue } from '@/utils/engineeringDisplay'

/** Matches backend phased navigation order in engine/graph/navigation_phases.py */
const PIPE_WALL_STEP_ORDER = [
  'pressure_loading',
  'design_pressure',
  'nominal_pipe_size',
  'outside_diameter',
  'material',
  'design_temperature',
  'external_design_pressure',
  'joint_category',
  'weld_joint_efficiency',
  'weld_strength_reduction',
  'temperature_coefficient',
  'corrosion_allowance',
] as const

function formatDisplayValue(value: unknown, unit?: string): string {
  return formatEngineeringDisplayValue(value, unit)
}

const MAWP_STEP_ORDER = [
  'nominal_pipe_size',
  'pipe_schedule',
  'outside_diameter',
  'actual_wall_thickness',
  'corrosion_allowance',
  'material',
  'design_temperature',
  'joint_category',
  'weld_joint_efficiency',
  'weld_strength_reduction',
  'temperature_coefficient',
] as const

function findNextWorkflowStep(workflowId: string, parameter: string): string | null {
  const order =
    workflowId === 'mawp_design'
      ? MAWP_STEP_ORDER
      : workflowId === 'pipe_wall_thickness_design'
        ? PIPE_WALL_STEP_ORDER
        : null
  if (!order) {
    return null
  }
  const index = order.indexOf(parameter as (typeof order)[number])
  if (index === -1 || index >= order.length - 1) {
    return null
  }
  return order[index + 1]
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
  const candidateNextStepId =
    state.workflow_id === 'pipe_wall_thickness_design' || state.workflow_id === 'mawp_design'
      ? findNextWorkflowStep(state.workflow_id, parameter)
      : null
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

  return {
    ...state,
    parameters,
    inputs: {
      ...state.inputs,
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
