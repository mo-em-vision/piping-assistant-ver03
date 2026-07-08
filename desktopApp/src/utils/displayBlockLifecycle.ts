import type { DisplayOutputBlock } from '@/types/backend/outputs'

export type DisplayLifecycle = 'durable' | 'preview' | 'volatile'

export type DisplayBlockWithLifecycle = DisplayOutputBlock & {
  lifecycle?: DisplayLifecycle
  display_role?: string
  display_channel?: string
  history_eligible?: boolean
  volatile?: boolean
}

const DURABLE_ROLES = new Set([
  'equation_trace',
  'substituted',
  'derived',
  'conclusion',
  'applicability',
  'recommendation',
  'result',
  'warning',
])

const PREVIEW_ROLES = new Set(['activation', 'preview'])

export function inferDisplayRole(block: DisplayOutputBlock): string | undefined {
  const candidate = block as DisplayBlockWithLifecycle
  if (candidate.display_role) {
    return candidate.display_role
  }

  const id = block.id
  if (id.startsWith('node-activation-equation-')) {
    return 'activation'
  }
  if (id.startsWith('equation-trace-')) {
    return 'equation_trace'
  }
  if (id.startsWith('path-preview-equation-')) {
    return 'preview'
  }
  if (id === 'path-calculation-substituted-equation' || id === 'mawp-substituted-equation') {
    return 'substituted'
  }
  if (id === 'minimum-thickness-equation') {
    return 'derived'
  }
  if (id.startsWith('path-preview-intro-')) {
    return 'intro'
  }
  if (id === 'minimum-thickness-conclusion') {
    return 'conclusion'
  }
  if (id === 'thin-wall-applicability-check') {
    return 'applicability'
  }
  if (id === 'pipe-schedule-recommendation') {
    return 'recommendation'
  }
  if (block.type === 'result') {
    return 'result'
  }
  if (block.type === 'warning' || (block.type === 'text' && block.variant === 'warning')) {
    return 'warning'
  }
  return undefined
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

/** Classify blocks with or without lifecycle metadata (legacy cache compatibility). */
export function inferDisplayLifecycle(block: DisplayOutputBlock): DisplayLifecycle {
  const candidate = block as DisplayBlockWithLifecycle
  if (candidate.lifecycle === 'durable' || candidate.lifecycle === 'preview' || candidate.lifecycle === 'volatile') {
    return candidate.lifecycle
  }

  if (candidate.volatile === true) {
    return 'volatile'
  }

  const id = block.id
  if (id === 'planning-status' || id.startsWith('archived-prompt-')) {
    return 'volatile'
  }

  const role = inferDisplayRole(block)
  if (role && DURABLE_ROLES.has(role)) {
    return 'durable'
  }

  if (id.startsWith('equation-trace-')) {
    return 'durable'
  }
  if (id.startsWith('path-preview-equation-') || id.startsWith('node-activation-equation-')) {
    return 'preview'
  }
  if (id.startsWith('path-preview-intro-')) {
    return 'preview'
  }

  if (role && PREVIEW_ROLES.has(role)) {
    return 'preview'
  }
  if (role === 'intro' && id.startsWith('path-preview-intro-')) {
    return 'preview'
  }

  return 'durable'
}

export function isVolatileDisplayBlock(block: DisplayOutputBlock): boolean {
  return inferDisplayLifecycle(block) === 'volatile'
}

export function isPreviewDisplayBlock(block: DisplayOutputBlock): boolean {
  return inferDisplayLifecycle(block) === 'preview'
}

export function isDurableDisplayBlock(block: DisplayOutputBlock): boolean {
  return inferDisplayLifecycle(block) === 'durable'
}

export function durableDisplayBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks.filter((block) => isDurableDisplayBlock(block))
}

export function previewDisplayBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks.filter((block) => isPreviewDisplayBlock(block))
}

export function previewBlocksByChannel(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  const byChannel = new Map<string, DisplayOutputBlock>()
  for (const block of blocks) {
    const channel = inferDisplayChannel(block) ?? block.id
    byChannel.set(channel, block)
  }
  return Array.from(byChannel.values())
}

export function equationTraceSemanticKey(
  block: DisplayOutputBlock,
  workflowId?: string | null,
): string | null {
  const candidate = block as DisplayBlockWithLifecycle
  const role = candidate.display_role ?? inferDisplayRole(block)
  if (role !== 'equation_trace' && !block.id.startsWith('equation-trace-')) {
    return null
  }
  const sourceNodeId = candidate.source_node_id
  const equationNodeId = candidate.equation_node_id
  if (!sourceNodeId || !equationNodeId) {
    return null
  }
  const workflow = workflowId ?? 'unknown'
  return `${workflow}|${sourceNodeId}|${equationNodeId}|equation_trace`
}

export function previewEquationSemanticKey(
  block: DisplayOutputBlock,
  workflowId?: string | null,
): string | null {
  if (!isPreviewDisplayBlock(block)) {
    return null
  }
  if (inferDisplayChannel(block) !== 'current_equation_preview') {
    return null
  }
  const candidate = block as DisplayBlockWithLifecycle
  const sourceNodeId = candidate.source_node_id
  const equationNodeId = candidate.equation_node_id
  if (!sourceNodeId || !equationNodeId) {
    return null
  }
  const workflow = workflowId ?? 'unknown'
  return `${workflow}|${sourceNodeId}|${equationNodeId}|equation_trace`
}
