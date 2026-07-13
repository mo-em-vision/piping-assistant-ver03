import { TextOutput } from './TextOutput'

import type { ParagraphContextOutputBlock, ProseRenderBlock } from '@/types/backend/outputs'

export function ParagraphContextOutput({ block }: { block: ParagraphContextOutputBlock }) {
  const prose: ProseRenderBlock = { ...block, variant: block.variant ?? 'body' }
  return <TextOutput block={prose} className="output-block--paragraph-context" />
}
