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

export { getCurrentEditableParameter, getWorkflowAsk } from './workflowAsk'
