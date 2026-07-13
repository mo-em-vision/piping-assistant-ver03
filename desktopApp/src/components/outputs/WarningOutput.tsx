import { TextOutput } from './TextOutput'

import type { ProseRenderBlock, WarningOutputBlock } from '@/types/backend/outputs'

export function WarningOutput({ block }: { block: WarningOutputBlock }) {
  const prose: ProseRenderBlock = { ...block, variant: block.variant ?? 'warning' }
  return <TextOutput block={prose} className="output-block--warning" />
}
