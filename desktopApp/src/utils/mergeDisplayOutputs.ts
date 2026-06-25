import type { DisplayOutputBlock } from '@/types/backend/outputs'

/** Append new workflow output blocks while preserving earlier step content. */
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

  const byId = new Map<string, DisplayOutputBlock>()
  for (const block of previous) {
    byId.set(block.id, block)
  }
  for (const block of incoming) {
    byId.set(block.id, block)
  }

  const orderedIds: string[] = []
  for (const block of previous) {
    if (!orderedIds.includes(block.id)) {
      orderedIds.push(block.id)
    }
  }
  for (const block of incoming) {
    if (!orderedIds.includes(block.id)) {
      orderedIds.push(block.id)
    }
  }

  return orderedIds.map((id) => byId.get(id)!)
}
