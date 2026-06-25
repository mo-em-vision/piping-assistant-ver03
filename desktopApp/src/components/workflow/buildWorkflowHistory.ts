import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
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

const PIPE_WALL_INPUT_STUBS: Record<
  string,
  Pick<ParameterDefinitionDto, 'label' | 'type' | 'units' | 'default_unit'>
> = {
  pressure_loading: {
    label: 'Pressure Loading',
    type: 'dropdown',
    units: [],
    default_unit: 'dimensionless',
  },
  material: { label: 'Material', type: 'material', units: [], default_unit: 'dimensionless' },
  design_pressure: {
    label: 'Design Pressure',
    type: 'number',
    units: ['bar', 'psi', 'MPa', 'kPa'],
    default_unit: 'bar',
  },
  design_temperature: {
    label: 'Design Temperature',
    type: 'number',
    units: ['C', 'F'],
    default_unit: 'C',
  },
  nominal_pipe_size: {
    label: 'Nominal Pipe Size',
    type: 'text',
    units: ['NPS', 'DN'],
    default_unit: 'NPS',
  },
  outside_diameter: {
    label: 'Outside Diameter',
    type: 'number',
    units: ['in', 'mm'],
    default_unit: 'in',
  },
  external_design_pressure: {
    label: 'External Design Pressure',
    type: 'number',
    units: ['bar', 'psi', 'MPa', 'kPa'],
    default_unit: 'bar',
  },
  joint_category: {
    label: 'Joint Category',
    type: 'dropdown',
    units: [],
    default_unit: 'dimensionless',
  },
  corrosion_allowance: {
    label: 'Corrosion Allowance',
    type: 'number',
    units: ['in', 'mm'],
    default_unit: 'mm',
  },
}

function stubParameterForStep(stepId: string): ParameterDefinitionDto | null {
  const spec = PIPE_WALL_INPUT_STUBS[stepId]
  if (!spec) {
    return null
  }

  return {
    name: stepId,
    label: spec.label,
    type: spec.type,
    required: true,
    units: spec.units,
    default_unit: spec.default_unit,
    default_value: null,
    value: null,
    options: null,
    validation: null,
    status: 'pending',
    requires_confirmation: false,
    submittable: true,
  }
}

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

    const stubId = submittableIds.find((id) => !NON_INPUT_ACTIVE_STEPS.has(id))
    if (stubId) {
      const stub = stubParameterForStep(stubId)
      if (stub) {
        return stub
      }
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

    const stub = stubParameterForStep(activeStepId)
    if (stub) {
      return stub
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
