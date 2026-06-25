import type { DisplayOutputBlock } from '@/types/backend/outputs'

/** Replace workflow output blocks with the latest backend snapshot. */
export function mergeDisplayOutputs(
  _previous: DisplayOutputBlock[],
  incoming: DisplayOutputBlock[],
): DisplayOutputBlock[] {
  return incoming
}
