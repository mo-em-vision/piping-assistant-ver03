import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

const HIDDEN_STEP_IDS = new Set([
  'straight_pipe_section',
  'd_input_mode',
  'thin_wall',
  'geometry_input_mode',
])

export const FORMULA_INPUT_STEP_IDS = new Set([
  'material',
  'design_pressure',
  'design_temperature',
  'nominal_pipe_size',
  'outside_diameter',
  'joint_category',
  'allowable_stress',
  'weld_joint_efficiency',
  'weld_strength_reduction',
  'temperature_coefficient',
])

export const USER_INPUT_STEP_PROMPT = 'Complete the fields below to continue.'

export function isHiddenWorkflowStep(stepId: string): boolean {
  return HIDDEN_STEP_IDS.has(stepId)
}

export function parameterNextStepPrompt(_parameter: ParameterDefinitionDto): string {
  return USER_INPUT_STEP_PROMPT
}

export function getNextStepPrompt(
  timeline: TimelineStepViewModel[],
  parameter: ParameterDefinitionDto | null,
): string | null {
  if (parameter) {
    return parameterNextStepPrompt(parameter)
  }

  const activeStep = timeline.find(
    (step) => step.status === 'active' && !isHiddenWorkflowStep(step.id),
  )
  if (activeStep?.id === 'thickness') {
    return 'Computing required wall thickness from the confirmed inputs.'
  }
  if (activeStep?.id === 'mawp') {
    return 'Computing Maximum Allowable Working Pressure (MAWP) from the confirmed inputs.'
  }

  if (!activeStep) {
    return null
  }

  return USER_INPUT_STEP_PROMPT
}

export function completedStepStatement(step: TimelineStepViewModel): string | null {
  if (!step.displayValue) {
    return null
  }

  switch (step.id) {
    case 'pressure_loading':
      return null
    case 'material':
    case 'design_pressure':
    case 'design_temperature':
    case 'nominal_pipe_size':
    case 'outside_diameter':
    case 'joint_category':
    case 'allowable_stress':
    case 'weld_joint_efficiency':
    case 'weld_strength_reduction':
    case 'temperature_coefficient':
      return null
    case 'd_input_mode':
    case 'thin_wall':
      return null
    case 'thickness':
      return `Required wall thickness: ${step.displayValue}.`
    case 'mawp':
      return `Maximum Allowable Working Pressure (MAWP): ${step.displayValue}.`
    default:
      return `${step.title}: ${step.displayValue}.`
  }
}
