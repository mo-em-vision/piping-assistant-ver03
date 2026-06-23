import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

export type WorkflowHistoryItem =
  | {
      id: string
      kind: 'prompt'
      title: string
      body?: string | null
      stepStatus: 'done' | 'active'
    }
  | {
      id: string
      kind: 'user-input'
      label: string
      value: string
    }
  | {
      id: string
      kind: 'output'
      block: DisplayOutputBlock
    }

function visibleTimelineSteps(timeline: TimelineStepViewModel[]): TimelineStepViewModel[] {
  const pendingIndex = timeline.findIndex((step) => step.status === 'pending')
  if (pendingIndex === -1) {
    return timeline
  }
  return timeline.slice(0, pendingIndex + 1).filter((step) => step.status !== 'pending')
}

export function buildWorkflowHistory(
  timeline: TimelineStepViewModel[],
  displayOutputs: DisplayOutputBlock[],
  inputs: Record<string, unknown> = {},
  parameters: ParameterDefinitionDto[] = [],
): WorkflowHistoryItem[] {
  const items: WorkflowHistoryItem[] = []
  const steps = visibleTimelineSteps(timeline)

  for (const step of steps) {
    items.push({
      id: `prompt-${step.id}`,
      kind: 'prompt',
      title: step.title,
      body: step.hint,
      stepStatus: step.status === 'done' ? 'done' : 'active',
    })

    if (step.status === 'done' && step.displayValue) {
      items.push({
        id: `input-${step.id}`,
        kind: 'user-input',
        label: step.title,
        value: step.displayValue,
      })
    }
  }

  const shownValues = new Set(
    items.filter((item) => item.kind === 'user-input').map((item) => item.value),
  )

  for (const [key, raw] of Object.entries(inputs)) {
    const record = raw as { display_value?: string; value?: unknown; unit?: string }
    const display =
      record.display_value ??
      (record.value != null
        ? `${String(record.value)}${record.unit && record.unit !== 'dimensionless' ? ` ${record.unit}` : ''}`
        : '')

    if (!display || shownValues.has(display)) {
      continue
    }

    const parameter = parameters.find((entry) => entry.name === key)
    items.push({
      id: `input-record-${key}`,
      kind: 'user-input',
      label: parameter?.label ?? key.replace(/_/g, ' '),
      value: display,
    })
    shownValues.add(display)
  }

  for (const block of displayOutputs) {
    items.push({
      id: `output-${block.id}`,
      kind: 'output',
      block,
    })
  }

  return items
}

export function getCurrentEditableParameter(state: TaskStateDto | null) {
  if (!state?.parameters?.length) {
    return null
  }

  return (
    state.parameters.find(
      (parameter) => parameter.status === 'pending' || parameter.status === 'confirmation_required',
    ) ?? null
  )
}
