import { NextWorkflowsOutput } from '@/components/outputs/NextWorkflowsOutput'

import type { NextWorkflowsOutputBlock } from '@/types/backend/outputs'

import './RelatedWorkflowsBlock.css'

interface RelatedWorkflowsBlockProps {
  block: NextWorkflowsOutputBlock
}

/** Bottom-panel related workflow suggestions (single editable block). */
export function RelatedWorkflowsBlock({ block }: RelatedWorkflowsBlockProps) {
  return (
    <section className="related-workflows-block" aria-label="Related workflows">
      <NextWorkflowsOutput block={block} />
    </section>
  )
}
