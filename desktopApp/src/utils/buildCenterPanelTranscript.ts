import type { DisplayOutputBlock } from '@/types/backend/outputs'
import {
  guidanceTranscriptToDisplayBlocks,
  type FlowGuidancePresentationBlock,
} from '@/utils/flowGuidanceTranscript'
import {
  inferDisplayRole,
  isPreviewDisplayBlock,
  isVolatileDisplayBlock,
  previewEquationSemanticKey,
  equationTraceSemanticKey,
} from '@/utils/displayBlockLifecycle'
import { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'

import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'

function reportRoleIndex(block: DisplayOutputBlock): number {
  const role = (block as { display_role?: string }).display_role ?? inferDisplayRole(block)
  const index = REPORT_ROLE_ORDER.indexOf(role)
  return index === -1 ? REPORT_ROLE_ORDER.length : index
}

function isEquationTraceBlock(block: DisplayOutputBlock): boolean {
  const role = inferDisplayRole(block)
  return role === 'equation_trace' || block.id.startsWith('equation-trace-')
}

function hideTraceDuplicateOfCurrentPreview(
  blocks: DisplayOutputBlock[],
  workflowId?: string | null,
): DisplayOutputBlock[] {
  const previewKeys = new Set(
    blocks
      .map((block) => previewEquationSemanticKey(block, workflowId))
      .filter((key): key is string => Boolean(key)),
  )

  if (previewKeys.size === 0) {
    return blocks
  }

  return blocks.filter((block) => {
    if (!isEquationTraceBlock(block)) {
      return true
    }
    const traceKey = equationTraceSemanticKey(block, workflowId)
    return !traceKey || !previewKeys.has(traceKey)
  })
}

function orderEngineeringBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  const traces: DisplayOutputBlock[] = []
  const durable: DisplayOutputBlock[] = []
  const previews: DisplayOutputBlock[] = []

  for (const block of blocks) {
    if (isPreviewDisplayBlock(block)) {
      previews.push(block)
      continue
    }
    if (isEquationTraceBlock(block)) {
      traces.push(block)
      continue
    }
    durable.push(block)
  }

  return [...traces, ...durable, ...previews]
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
  const guidanceBlocks = guidanceTranscriptToDisplayBlocks(transcriptBlocks)
  const guidanceIds = new Set(guidanceBlocks.map((block) => block.id))

  const engineering = displayOutputs.filter(
    (block) => !guidanceIds.has(block.id) && !isVolatileDisplayBlock(block),
  )
  const dedupedEngineering = hideTraceDuplicateOfCurrentPreview(engineering, workflowId)
  const orderedEngineering = orderEngineeringBlocks(dedupedEngineering)

  const merged = dedupeByBlockId([...guidanceBlocks, ...orderedEngineering])
  const ordered = sortByReportOrder(merged)

  return ordered.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output' as const,
    block,
  }))
}

export { REPORT_ROLE_ORDER } from '@/utils/centerPanelContract'
