import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'
import {
  equationTraceSemanticKey,
  inferDisplayRole,
  isPreviewDisplayBlock,
  isVolatileDisplayBlock,
  previewEquationSemanticKey,
} from '@/utils/displayBlockLifecycle'

export type WorkflowHistoryItem = {
  id: string
  kind: 'output'
  block: DisplayOutputBlock
}

function isEquationTraceBlock(block: DisplayOutputBlock): boolean {
  const role = inferDisplayRole(block)
  return role === 'equation_trace' || block.id.startsWith('equation-trace-')
}

function orderDisplayBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
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

export function buildWorkflowHistory(
  _timeline: TimelineStepViewModel[],
  displayOutputs: DisplayOutputBlock[],
  workflowId?: string | null,
): WorkflowHistoryItem[] {
  const filtered = displayOutputs.filter((block) => !isVolatileDisplayBlock(block))
  const deduped = hideTraceDuplicateOfCurrentPreview(filtered, workflowId)
  const ordered = orderDisplayBlocks(deduped)

  return ordered.map((block) => ({
    id: `output-${block.id}`,
    kind: 'output',
    block,
  }))
}

export { getCurrentEditableParameter, getWorkflowAsk } from './workflowAsk'
