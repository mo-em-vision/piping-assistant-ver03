import type { ReferenceOutputBlock } from '@/types/backend/outputs'

interface ReferenceOutputProps {
  block: ReferenceOutputBlock
}

export function ReferenceOutput({ block }: ReferenceOutputProps) {
  const meta = [block.standard, block.paragraph, block.table, block.figure].filter(Boolean).join(' · ')

  return (
    <article className="output-block output-reference">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      {meta ? <p className="output-reference__meta">{meta}</p> : null}
      {block.excerpt ? <p className="output-reference__excerpt">{block.excerpt}</p> : null}
      {block.source_node ? <p className="output-reference__source">Source node: {block.source_node}</p> : null}
    </article>
  )
}
