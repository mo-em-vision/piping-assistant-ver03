import type { DisplayOutputBlock } from '@/types/backend/outputs'

import {
  inferDisplayLifecycle,
  isVolatileDisplayBlock,
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
  const merged = [...durablePrevious]

  for (const block of durableIncoming) {
    const existingIndex = indexById.get(block.id)
    if (existingIndex !== undefined) {
      merged[existingIndex] = block
      continue
    }

    indexById.set(block.id, merged.length)
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
 * - durable blocks update/append by stable block id only
 * - preview blocks (non-equation) replace by display_channel when present
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

  const previewByChannel = new Map<string, DisplayOutputBlock>()
  for (const block of previewIncoming) {
    if (block.type === 'equation' || block.id.startsWith('equation-')) {
      continue
    }
    const channel = (block as { display_channel?: string }).display_channel ?? block.id
    previewByChannel.set(channel, block)
  }

  return [...mergedDurable, ...Array.from(previewByChannel.values())]
}

export { isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
