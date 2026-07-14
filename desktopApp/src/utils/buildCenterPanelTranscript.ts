import type { DisplayOutputBlock, NextWorkflowsOutputBlock } from '@/types/backend/outputs'
import { filterRegisteredCenterPanelBlocks } from '@/utils/centerPanelBlockRegistry'
import {
  guidanceTranscriptToDisplayBlocks,
  containsInternalLeakText,
  type FlowGuidancePresentationBlock,
} from '@/utils/flowGuidanceTranscript'
import { isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
import { blockDisplayRole, reportRoleIndex, REPORT_ROLE_ORDER } from '@/utils/displayRole'

import type { WorkflowHistoryItem } from '@/components/workflow/buildWorkflowHistory'

export type CenterPanelTranscriptParts = {
  historyItems: WorkflowHistoryItem[]
  relatedWorkflowsBlock: NextWorkflowsOutputBlock | null
}

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

function isUserVisibleBlock(block: DisplayOutputBlock): boolean {
  const content = String(
    ('content' in block ? block.content : '') ||
      ('text' in block ? (block as { text?: string }).text : '') ||
      '',
  ).trim()
  const title = String(block.title ?? '').trim()
  if (content && containsInternalLeakText(content)) {
    return false
  }
  if (title && containsInternalLeakText(title)) {
    return false
  }
  return true
}

function isNextWorkflowsBlock(block: DisplayOutputBlock): block is NextWorkflowsOutputBlock {
  return block.type === 'next_workflows' || blockDisplayRole(block) === 'next_workflows'
}

function pickRelatedWorkflowsBlock(
  blocks: DisplayOutputBlock[],
): NextWorkflowsOutputBlock | null {
  for (let index = blocks.length - 1; index >= 0; index -= 1) {
    const block = blocks[index]
    if (isNextWorkflowsBlock(block)) {
      return block
    }
  }
  return null
}

/**
 * Merge durable flow_guidance.transcript_blocks with engineering display_outputs.
 * Related workflow suggestions are returned separately for the bottom footer.
 */
export function buildCenterPanelTranscriptParts(
  displayOutputs: DisplayOutputBlock[],
  transcriptBlocks: FlowGuidancePresentationBlock[] | unknown[],
  workflowId?: string | null,
): CenterPanelTranscriptParts {
  void workflowId
  const allGuidance = filterRegisteredCenterPanelBlocks(
    guidanceTranscriptToDisplayBlocks(transcriptBlocks),
  )
    .filter((block) => {
      const role = blockDisplayRole(block)
      return role !== 'ask_archive' && role !== 'answer_archive'
    })
    .filter(isUserVisibleBlock)

  const guidanceIds = new Set(allGuidance.map((block) => block.id))

  const engineering = filterRegisteredCenterPanelBlocks(
    displayOutputs.filter(
      (block) =>
        !guidanceIds.has(block.id) &&
        (!isVolatileDisplayBlock(block) || blockDisplayRole(block) === 'input_waiting') &&
        isUserVisibleBlock(block),
    ),
  )

  const merged = sortByReportRole(dedupeByBlockId([...allGuidance, ...engineering]))
  const relatedWorkflowsBlock = pickRelatedWorkflowsBlock(merged)
  const scrollBlocks = merged.filter((block) => !isNextWorkflowsBlock(block))

  return {
    historyItems: scrollBlocks.map((block) => ({
      id: `output-${block.id}`,
      kind: 'output' as const,
      block,
    })),
    relatedWorkflowsBlock,
  }
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
  return buildCenterPanelTranscriptParts(displayOutputs, transcriptBlocks, workflowId).historyItems
}

export { REPORT_ROLE_ORDER } from '@/utils/displayRole'
