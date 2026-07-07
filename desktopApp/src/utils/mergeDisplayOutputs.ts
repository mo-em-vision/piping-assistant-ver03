import type { DisplayOutputBlock } from '@/types/backend/outputs'

/** Append new workflow output blocks; update in place when ids match; never remove prior blocks. */
export function mergeDisplayOutputs(
  previous: DisplayOutputBlock[],
  incoming: DisplayOutputBlock[],
): DisplayOutputBlock[] {
  if (incoming.length === 0) {
    return previous
  }
  if (previous.length === 0) {
    return incoming
  }

  const indexById = new Map(previous.map((block, index) => [block.id, index]))
  const merged = [...previous]

  for (const block of incoming) {
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
