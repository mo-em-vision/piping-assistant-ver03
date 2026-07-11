import type { DisplayOutputBlock } from '@/types/backend/outputs'
import {
  guidanceTranscriptToDisplayBlocks,
  type FlowGuidancePresentationBlock,
} from '@/utils/flowGuidanceTranscript'
import { isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
import { blockDisplayRole, reportRoleIndex, REPORT_ROLE_ORDER } from '@/utils/displayRole'

import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'

function dedupeByBlockId(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  const winners = new Map<string, DisplayOutputBlock>()
  const order: string[] = []
  for (const block of blocks) {
    if (winners.has(block.id)) {
      winners.set(block.id, block)
      continue
    }
    winners.set(block.id, block)
    order.push(block.id)
  }
  return order.map((id) => winners.get(id)!)
}

function sortByReportRole(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return [...blocks]
    .map((block, index) => ({ block, index, role: blockDisplayRole(block) }))
    .sort((left, right) => {
      const roleDelta = reportRoleIndex(left.role) - reportRoleIndex(right.role)
      if (roleDelta !== 0) {
        return roleDelta
      }
      return left.index - right.index
    })
    .map((item) => item.block)
}

/**
 * Merge durable flow_guidance.transcript_blocks with engineering display_outputs.
 * Blocks are ordered by the shared REPORT_ROLE_ORDER contract.
 */
export function buildCenterPanelTranscript(
  displayOutputs: DisplayOutputBlock[],
  transcriptBlocks: FlowGuidancePresentationBlock[] | unknown[],
  workflowId?: string | null,
): WorkflowHistoryItem[] {
  void workflowId
  const allGuidance = guidanceTranscriptToDisplayBlocks(transcriptBlocks).filter((block) => {
    const role = blockDisplayRole(block)
    return role !== 'ask_archive' && role !== 'answer_archive'
  })

  const guidanceIds = new Set(allGuidance.map((block) => block.id))

  const engineering = displayOutputs.filter(
    (block) => !guidanceIds.has(block.id) && !isVolatileDisplayBlock(block),
  )

  const merged = sortByReportRole(dedupeByBlockId([...allGuidance, ...engineering]))

  return merged.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output' as const,
    block,
  }))
}

export { REPORT_ROLE_ORDER } from '@/utils/displayRole'
