import type { DisplayOutputBlock } from '@/types/backend/outputs'

import {
  inferDisplayLifecycle,
  isPreviewEquationBlock,
  isVolatileDisplayBlock,
  mergeEquationTraceHistoryKey,
} from '@/utils/displayBlockLifecycle'
import { blockDisplayRole } from '@/utils/displayRole'

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

function mergePreviewEquationBlocks(
  previewPrevious: DisplayOutputBlock[],
  previewIncoming: DisplayOutputBlock[],
  durableEquationKeys: Set<string>,
): DisplayOutputBlock[] {
  const byKey = new Map<string, DisplayOutputBlock>()

  for (const block of previewPrevious) {
    if (!isPreviewEquationBlock(block)) {
      continue
    }
    const key = mergeEquationTraceHistoryKey(block)
    if (!isStablePreviewEquationKey(key) || durableEquationKeys.has(key)) {
      continue
    }
    byKey.set(key, block)
  }

  for (const block of previewIncoming) {
    if (!isPreviewEquationBlock(block)) {
      continue
    }
    const key = mergeEquationTraceHistoryKey(block) ?? block.id
    if (durableEquationKeys.has(key)) {
      continue
    }
    byKey.set(key, block)
  }

  return Array.from(byKey.values())
}

function isStablePreviewEquationKey(key: string | null): key is string {
  return Boolean(key?.startsWith('equation-'))
}

function collectInputWaitingBlocks(blocks: DisplayOutputBlock[]): DisplayOutputBlock[] {
  return blocks.filter((block) => blockDisplayRole(block) === 'input_waiting')
}

/**
 * Merge display outputs by lifecycle:
 * - durable blocks update/append by stable block id only
 * - preview equation blocks keyed by stable equation id; retain visited previews from previous
 * - other preview blocks replace by display_channel when present
 * - volatile blocks are dropped except ephemeral input_waiting from the incoming snapshot
 */
export function mergeDisplayOutputs(
  previous: DisplayOutputBlock[],
  incoming: DisplayOutputBlock[],
): DisplayOutputBlock[] {
  const filteredPrevious = withoutVolatileBlocks(previous)
  const filteredIncoming = withoutVolatileBlocks(incoming)
  const inputWaiting = collectInputWaitingBlocks(incoming)

  const { durable: durablePrevious, preview: previewPrevious } =
    partitionByLifecycle(filteredPrevious)
  const { durable: durableIncoming, preview: previewIncoming } =
    partitionByLifecycle(filteredIncoming)

  const mergedDurable = mergeDurableBlocks(durablePrevious, durableIncoming)
  const durableEquationKeys = new Set(
    mergedDurable
      .map((block) => mergeEquationTraceHistoryKey(block))
      .filter((key): key is string => key != null),
  )

  const previewByChannel = new Map<string, DisplayOutputBlock>()
  for (const block of previewIncoming) {
    if (isPreviewEquationBlock(block)) {
      continue
    }
    const channel = (block as { display_channel?: string }).display_channel ?? block.id
    previewByChannel.set(channel, block)
  }

  const previewEquations = mergePreviewEquationBlocks(
    previewPrevious,
    previewIncoming,
    durableEquationKeys,
  )

  return [
    ...mergedDurable,
    ...previewEquations,
    ...Array.from(previewByChannel.values()),
    ...inputWaiting,
  ]
}

export { isVolatileDisplayBlock } from '@/utils/displayBlockLifecycle'
