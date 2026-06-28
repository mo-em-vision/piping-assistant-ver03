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

export function isHiddenWorkflowStep(stepId: string): boolean {
  return HIDDEN_STEP_IDS.has(stepId)
}

export const PIPE_MATERIAL_PROMPT =
  'Select the pipe material. (start typing to see the available options)'

export function parameterNextStepPrompt(parameter: ParameterDefinitionDto): string {
  switch (parameter.name) {
    case 'pressure_loading':
      return 'Specify whether the pipe is internally or externally pressurized.'
    case 'material':
      return PIPE_MATERIAL_PROMPT
    case 'design_pressure':
      return 'Enter the design pressure for the pipe.'
    case 'design_temperature':
      return 'Enter the design temperature for the pipe.'
    case 'nominal_pipe_size':
      return 'Enter the nominal pipe size.'
    case 'pipe_schedule':
      return 'Enter the pipe schedule (for example 40, 80, or STD).'
    case 'actual_wall_thickness':
      return 'Enter the actual or ordered wall thickness of the pipe.'
    case 'outside_diameter':
      return 'Enter the outside diameter of the pipe.'
    case 'corrosion_allowance':
      return 'Enter the corrosion allowance for the pressure design thickness calculation (t = t_actual - c).'
    default:
      if (parameter.type === 'material') {
        return PIPE_MATERIAL_PROMPT
      }
      return `Enter ${parameter.label.toLowerCase()}.`
  }
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

  return activeStepPrompt(activeStep).body
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

export function activeStepPrompt(step: TimelineStepViewModel): { body: string; hint?: string | null } {
  switch (step.id) {
    case 'pressure_loading':
      return {
        body: 'Specify whether the pipe is internally or externally pressurized.',
        hint: step.hint,
      }
    case 'material':
      return {
        body: PIPE_MATERIAL_PROMPT,
        hint: step.hint,
      }
    case 'design_pressure':
      return {
        body: 'Enter the design pressure for the pipe.',
        hint: step.hint,
      }
    case 'design_temperature':
      return {
        body: 'Enter the design temperature for the pipe.',
        hint: step.hint,
      }
    default:
      return {
        body: step.hint ?? step.title,
        hint: null,
      }
  }
}
