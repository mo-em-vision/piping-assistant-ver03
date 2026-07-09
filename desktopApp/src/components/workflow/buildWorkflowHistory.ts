import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'
import { inferDisplayRole, isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
import { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'

export type WorkflowHistoryItem = {
  id: string
  kind: 'output'
  block: DisplayOutputBlock
}

function reportRoleIndex(block: DisplayOutputBlock): number {
  const role = (block as { display_role?: string }).display_role ?? inferDisplayRole(block)
  const index = REPORT_ROLE_ORDER.indexOf(role)
  return index === -1 ? REPORT_ROLE_ORDER.length : index
}

export function buildWorkflowHistory(
  _timeline: TimelineStepViewModel[],
  displayOutputs: DisplayOutputBlock[],
  _workflowId?: string | null,
): WorkflowHistoryItem[] {
  const filtered = displayOutputs.filter((block) => !isVolatileDisplayBlock(block))
  const ordered = [...filtered].sort((left, right) => {
    const leftIndex = reportRoleIndex(left)
    const rightIndex = reportRoleIndex(right)
    if (leftIndex !== rightIndex) {
      return leftIndex - rightIndex
    }
    return 0
  })

  return ordered.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output',
    block,
  }))
}

export { getCurrentEditableParameter, getWorkflowAsk } from './workflowAsk'
