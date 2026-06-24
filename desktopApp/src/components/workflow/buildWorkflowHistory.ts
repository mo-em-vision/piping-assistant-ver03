import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

import {
  completedStepStatement,
  FORMULA_INPUT_STEP_IDS,
  isHiddenWorkflowStep,
} from './workflowReport'

export type WorkflowHistoryItem =
  | {
      id: string
      kind: 'report-statement'
      body: string
    }
  | {
      id: string
      kind: 'node-content'
      block: DisplayOutputBlock
    }
  | {
      id: string
      kind: 'output'
      block: DisplayOutputBlock
    }

function visibleTimelineSteps(timeline: TimelineStepViewModel[]): TimelineStepViewModel[] {
  const pendingIndex = timeline.findIndex((step) => step.status === 'pending')
  const visible =
    pendingIndex === -1
      ? timeline
      : timeline.slice(0, pendingIndex + 1).filter((step) => step.status !== 'pending')
  return visible.filter((step) => !isHiddenWorkflowStep(step.id))
}

function isHistoryOutputBlock(block: DisplayOutputBlock): boolean {
  if (block.id.startsWith('node-activation-')) {
    return false
  }
  if (block.id === 'planning-status') {
    return false
  }
  if (block.id.startsWith('path-preview-reference-')) {
    return false
  }
  return true
}

export function buildWorkflowHistory(
  timeline: TimelineStepViewModel[],
  displayOutputs: DisplayOutputBlock[],
): WorkflowHistoryItem[] {
  const items: WorkflowHistoryItem[] = []

  const activationBlocks = displayOutputs.filter(
    (block) =>
      block.id.startsWith('node-activation-') && !block.id.startsWith('node-activation-reference-'),
  )
  const otherBlocks = displayOutputs.filter(isHistoryOutputBlock)

  for (const block of activationBlocks) {
    items.push({
      id: `node-content-${block.id}`,
      kind: 'node-content',
      block,
    })
  }

  for (const block of otherBlocks) {
    items.push({
      id: `output-${block.id}`,
      kind: 'output',
      block,
    })
  }

  const steps = visibleTimelineSteps(timeline)

  for (const step of steps) {
    if (step.status !== 'done' || FORMULA_INPUT_STEP_IDS.has(step.id)) {
      continue
    }
    const statement = completedStepStatement(step)
    if (statement) {
      items.push({
        id: `statement-${step.id}`,
        kind: 'report-statement',
        body: statement,
      })
    }
  }

  return items
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

function firstEditableParameter(state: TaskStateDto) {
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
