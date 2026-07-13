import { TextOutput } from './TextOutput'

import type { ProseRenderBlock, ResultSummaryOutputBlock } from '@/types/backend/outputs'

export function ResultSummaryOutput({ block }: { block: ResultSummaryOutputBlock }) {
  const prose: ProseRenderBlock = { ...block, variant: block.variant ?? 'body' }
  return <TextOutput block={prose} className="output-block--result-summary" />
}
