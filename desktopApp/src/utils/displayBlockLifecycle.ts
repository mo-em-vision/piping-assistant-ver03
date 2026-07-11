import type { DisplayOutputBlock } from '@/types/backend/outputs'

import {
  blockDisplayRole,
  lifecycleForEquationState,
  resolveDisplayBlock,
  type DisplayBlockWithRole,
  type DisplayState,
} from '@/utils/displayRole'

export type DisplayLifecycle = 'durable' | 'preview' | 'volatile'

export type DisplayBlockWithLifecycle = DisplayBlockWithRole

const DURABLE_NON_EQUATION_ROLES = new Set([
  'result_summary',
  'applicability',
  'lookup_table_recommendation',
  'warning',
  'engineering_reference',
  'paragraph_context',
])

export function inferDisplayRole(block: DisplayOutputBlock): string | undefined {
  return blockDisplayRole(block) || undefined
}

export function inferDisplayChannel(block: DisplayOutputBlock): string | null {
  const candidate = block as DisplayBlockWithLifecycle
  if (candidate.display_channel) {
    return candidate.display_channel
  }

  const id = block.id
  if (id.startsWith('path-preview-equation-') || id.startsWith('node-activation-equation-')) {
    return 'current_equation_preview'
  }
  if (id.startsWith('path-preview-intro-')) {
    return 'current_node_intro'
  }
  return null
}

export function inferDisplayLifecycle(block: DisplayOutputBlock): DisplayLifecycle {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  if (candidate.lifecycle === 'durable' || candidate.lifecycle === 'preview' || candidate.lifecycle === 'volatile') {
    return candidate.lifecycle
  }

  if (candidate.volatile === true) {
    return 'volatile'
  }
  if (candidate.history_eligible === false) {
    return 'volatile'
  }

  const role = candidate.display_role ?? ''
  if (role === 'equation') {
    return lifecycleForEquationState(candidate.display_state)
  }

  const id = block.id
  if (id.startsWith('equation-') && !id.startsWith('equation-trace-')) {
    return lifecycleForEquationState(candidate.display_state)
  }
  if (id.startsWith('path-preview-equation-') || id.startsWith('node-activation-equation-')) {
    return 'preview'
  }
  if (id.startsWith('path-preview-intro-')) {
    return 'preview'
  }
  if (DURABLE_NON_EQUATION_ROLES.has(role)) {
    return 'durable'
  }
  if (role === 'node_intro' && id.startsWith('path-preview-intro-')) {
    return 'preview'
  }

  return 'durable'
}

export function isVolatileDisplayBlock(block: DisplayOutputBlock): boolean {
  const candidate = block as DisplayBlockWithLifecycle
  if (candidate.lifecycle === 'volatile' || candidate.volatile === true) {
    return true
  }
  if (candidate.history_eligible === false && inferDisplayLifecycle(block) === 'volatile') {
    return true
  }
  const id = block.id
  return id === 'planning-status' || id === 'input-waiting' || id.startsWith('archived-prompt-')
}

export function isPreviewEquationBlock(block: DisplayOutputBlock): boolean {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  return (
    candidate.display_role === 'equation' &&
    (candidate.display_state === 'preview' || candidate.display_state === 'active')
  )
}

export function durableDisplayBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks.filter((block) => inferDisplayLifecycle(block) === 'durable')
}

export function equationTraceSemanticKey(
  workflow: string,
  sourceNodeId: string,
  equationNodeId: string,
): string {
  return `${workflow}|${sourceNodeId}|${equationNodeId}|equation`
}

export function isEquationDisplayBlock(block: DisplayOutputBlock): boolean {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  return candidate.display_role === 'equation'
}

export function equationDisplayState(block: DisplayOutputBlock): DisplayState | undefined {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  return candidate.display_state
}

export function shouldRetainEquationBlock(
  block: DisplayOutputBlock,
  workflowId: string | undefined,
): boolean {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  if (candidate.display_role !== 'equation') {
    return true
  }
  if (!workflowId) {
    return true
  }
  const equationNodeId = String(
    (candidate as { equation_node_id?: string }).equation_node_id ?? '',
  ).trim()
  const sourceNodeId = String((candidate as { source_node_id?: string }).source_node_id ?? '').trim()
  if (!equationNodeId || !sourceNodeId) {
    return true
  }
  return Boolean(equationTraceSemanticKey(workflowId, sourceNodeId, equationNodeId))
}

export function isStableEquationBlockId(blockId: string): boolean {
  return blockId.startsWith('equation-') && !blockId.startsWith('equation-trace-')
}

export function mergeEquationTraceHistoryKey(block: DisplayOutputBlock): string | null {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  if (candidate.display_role !== 'equation') {
    return null
  }
  const equationNodeId = String(
    (candidate as { equation_node_id?: string }).equation_node_id ?? '',
  ).trim()
  if (!equationNodeId) {
    return candidate.id
  }
  return `equation-${equationNodeId}`
}

export function isPreviewTierEquationBlock(block: DisplayOutputBlock): boolean {
  const candidate = resolveDisplayBlock(block as DisplayBlockWithRole)
  if (candidate.display_role !== 'equation') {
    return false
  }
  if (inferDisplayChannel(block) !== 'current_equation_preview') {
    return false
  }
  return candidate.display_state === 'preview' || candidate.display_state === 'active'
}

export function equationHistoryKey(
  workflow: string,
  sourceNodeId: string,
  equationNodeId: string,
): string {
  return equationTraceSemanticKey(workflow, sourceNodeId, equationNodeId)
}
