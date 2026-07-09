import type { DisplayOutputBlock } from '@/types/backend/outputs'
import {
  guidanceTranscriptToDisplayBlocks,
  type FlowGuidancePresentationBlock,
} from '@/utils/flowGuidanceTranscript'
import { inferDisplayRole, isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'

import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'

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

function blockRole(block: DisplayOutputBlock): string {
  return (block as { display_role?: string }).display_role ?? inferDisplayRole(block)
}

/**
 * Merge durable flow_guidance.transcript_blocks with engineering display_outputs.
 * Workflow intro appears first; new guidance narration appends after engineering blocks.
 */
export function buildCenterPanelTranscript(
  displayOutputs: DisplayOutputBlock[],
  transcriptBlocks: FlowGuidancePresentationBlock[] | unknown[],
  workflowId?: string | null,
): WorkflowHistoryItem[] {
  void workflowId
  const allGuidance = guidanceTranscriptToDisplayBlocks(transcriptBlocks).filter((block) => {
    const role = blockRole(block)
    return role !== 'ask_archive' && role !== 'answer_archive'
  })

  const workflowIntro = allGuidance.filter((block) => blockRole(block) === 'workflow_intro')
  const guidanceNarration = allGuidance.filter((block) => blockRole(block) !== 'workflow_intro')
  const guidanceIds = new Set(allGuidance.map((block) => block.id))

  const engineering = displayOutputs.filter(
    (block) => !guidanceIds.has(block.id) && !isVolatileDisplayBlock(block),
  )

  const merged = dedupeByBlockId([...workflowIntro, ...engineering, ...guidanceNarration])

  return merged.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output' as const,
    block,
  }))
}

export { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'
