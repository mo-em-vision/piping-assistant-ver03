import type { DisplayOutputBlock } from '@/types/backend/outputs'

import {
  equationTraceSemanticKey,
  inferDisplayLifecycle,
  inferDisplayRole,
  isVolatileDisplayBlock,
  previewBlocksByChannel,
  previewEquationSemanticKey,
} from '@/utils/displayBlockLifecycle'

function withoutVolatileBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks.filter((block) => !isVolatileDisplayBlock(block))
}

function mergeDurableBlocks(
  durablePrevious: DisplayOutputBlock[],
  durableIncoming: DisplayOutputBlock[],
): DisplayOutputBlock[] {
  if (durableIncoming.length === 0) {
    return durablePrevious
  }
  if (durablePrevious.length === 0) {
    return durableIncoming
  }

  const indexById = new Map(durablePrevious.map((block, index) => [block.id, index]))
  const indexByTraceKey = new Map<string, number>()
  const merged = [...durablePrevious]

  for (const [index, block] of durablePrevious.entries()) {
    const traceKey = equationTraceSemanticKey(block)
    if (traceKey) {
      indexByTraceKey.set(traceKey, index)
    }
  }

  for (const block of durableIncoming) {
    const traceKey = equationTraceSemanticKey(block)
    if (traceKey) {
      const existingByKey = indexByTraceKey.get(traceKey)
      if (existingByKey !== undefined) {
        merged[existingByKey] = block
        indexById.set(block.id, existingByKey)
        continue
      }
    }

    const existingIndex = indexById.get(block.id)
    if (existingIndex !== undefined) {
      merged[existingIndex] = block
      if (traceKey) {
        indexByTraceKey.set(traceKey, existingIndex)
      }
      continue
    }

    indexById.set(block.id, merged.length)
    if (traceKey) {
      indexByTraceKey.set(traceKey, merged.length)
    }
    merged.push(block)
  }

  return merged
}

function partitionByLifecycle(blocks: DisplayOutputBlock[]): {
  durable: DisplayOutputBlock[]
  preview: DisplayOutputBlock[]
} {
  const durable: DisplayOutputBlock[] = []
  const preview: DisplayOutputBlock[] = []

  for (const block of blocks) {
    const lifecycle = inferDisplayLifecycle(block)
    if (lifecycle === 'volatile') {
      continue
    }
    if (lifecycle === 'preview') {
      preview.push(block)
      continue
    }
    durable.push(block)
  }

  return { durable, preview }
}

/**
 * Merge display outputs by lifecycle:
 * - durable blocks append/update by stable id (legacy cache may omit lifecycle metadata)
 * - preview blocks are authoritative from the incoming snapshot (replace by display_channel)
 * - volatile blocks are dropped
 */
export function mergeDisplayOutputs(
  previous: DisplayOutputBlock[],
  incoming: DisplayOutputBlock[],
): DisplayOutputBlock[] {
  const filteredPrevious = withoutVolatileBlocks(previous)
  const filteredIncoming = withoutVolatileBlocks(incoming)

  const { durable: durablePrevious } = partitionByLifecycle(filteredPrevious)
  const { durable: durableIncoming, preview: previewIncoming } = partitionByLifecycle(filteredIncoming)

  const mergedDurable = mergeDurableBlocks(durablePrevious, durableIncoming)
  const mergedPreview = previewBlocksByChannel(previewIncoming)

  return [...mergedDurable, ...mergedPreview]
}

export { isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
