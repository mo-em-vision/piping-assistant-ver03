import type { DisplayOutputBlock } from '@/types/backend/outputs'
import {
  guidanceTranscriptToDisplayBlocks,
  type FlowGuidancePresentationBlock,
} from '@/utils/flowGuidanceTranscript'
import { inferDisplayRole, isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
import { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'

import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'

function reportRoleIndex(block: DisplayOutputBlock): number {
  const role = (block as { display_role?: string }).display_role ?? inferDisplayRole(block)
  const index = REPORT_ROLE_ORDER.indexOf(role)
  return index === -1 ? REPORT_ROLE_ORDER.length : index
}

function dedupeByBlockId(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  const seen = new Set<string>()
  const ordered: DisplayOutputBlock[] = []
  for (const block of blocks) {
    if (seen.has(block.id)) {
      continue
    }
    seen.add(block.id)
    ordered.push(block)
  }
  return ordered
}

function sortByReportOrder(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks
    .map((block, index) => ({ block, index, roleIndex: reportRoleIndex(block) }))
    .sort((left, right) => {
      if (left.roleIndex !== right.roleIndex) {
        return left.roleIndex - right.roleIndex
      }
      return left.index - right.index
    })
    .map((entry) => entry.block)
}

/**
 * Merge durable flow_guidance.transcript_blocks with engineering display_outputs.
 * Uses backend transcript as the only guidance source (not presentation_blocks).
 */
export function buildCenterPanelTranscript(
  displayOutputs: DisplayOutputBlock[],
  transcriptBlocks: FlowGuidancePresentationBlock[] | unknown[],
  workflowId?: string | null,
): WorkflowHistoryItem[] {
  void workflowId
  const guidanceBlocks = guidanceTranscriptToDisplayBlocks(transcriptBlocks).filter((block) => {
    const role = (block as { display_role?: string }).display_role
    return (
      role !== 'workflow_intro' && role !== 'ask_archive' && role !== 'answer_archive'
    )
  })
  const guidanceIds = new Set(guidanceBlocks.map((block) => block.id))

  const engineering = displayOutputs.filter(
    (block) => !guidanceIds.has(block.id) && !isVolatileDisplayBlock(block),
  )

  const merged = dedupeByBlockId([...guidanceBlocks, ...engineering])
  const ordered = sortByReportOrder(merged)

  return ordered.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output' as const,
    block,
  }))
}

export { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'
