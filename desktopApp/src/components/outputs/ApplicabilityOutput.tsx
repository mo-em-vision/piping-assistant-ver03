import { TextOutput } from './TextOutput'

import type { ApplicabilityOutputBlock, ProseRenderBlock } from '@/types/backend/outputs'

export function ApplicabilityOutput({ block }: { block: ApplicabilityOutputBlock }) {
  const prose: ProseRenderBlock = { ...block, variant: block.variant ?? 'body' }
  return <TextOutput block={prose} className="output-block--applicability" />
}
