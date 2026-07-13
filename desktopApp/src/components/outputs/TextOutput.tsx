import { EngineeringMathText } from '@/components/math/engineeringMath'
import { InlineCitationList, InlineCitationText } from '@/components/standards/InlineCitationText'

import type { ProseRenderBlock, ReferenceChipDto, ReferenceLinkDto } from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'

interface TextOutputProps {
  block: ProseRenderBlock
  className?: string
}

function isInlinePlacement(block: ProseRenderBlock): boolean {
  return block.reference_links_placement !== 'below'
}

function renderInlineReferences(block: ProseRenderBlock) {
  const chips = block.reference_chips ?? []
  const links = block.reference_links ?? []

  if (chips.length) {
    return <InlineCitationList chips={chips} className="output-text__inline-references" />
  }

  if (!links.length) {
    return null
  }

  return (
    <>
      {links.map((link, index) => (
        <span key={link.node_id}>
          {index === 0 ? ' ' : ', '}
          <InlineCitationText link={link} linkLabel={link.label} />
        </span>
      ))}
    </>
  )
}

export function TextOutput({ block, className }: TextOutputProps) {
  const variantClass =
    block.variant === 'warning'
      ? 'output-text output-text--warning'
      : block.variant === 'caption'
        ? 'output-text output-text--caption'
        : block.variant === 'assumption'
          ? 'output-text output-text--assumption'
          : 'output-text'
  const inlineReferences = isInlinePlacement(block)
  const hasReferences = Boolean(block.reference_chips?.length || block.reference_links?.length)

  return (
    <article className={`output-block${className ? ` ${className}` : ''}`}>
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <p className={variantClass}>
        {block.variant === 'assumption' ? (
          <>
            <strong className="output-text__assumption-label">Assumptions:</strong>{' '}
          </>
        ) : null}
        <EngineeringMathText text={block.content} />
        {inlineReferences && hasReferences ? renderInlineReferences(block) : null}
        {block.content_suffix ? <EngineeringMathText text={block.content_suffix} /> : null}
      </p>
      {!inlineReferences && hasReferences ? (
        <p className="output-text output-text--references">
          {renderInlineReferences(block)}
        </p>
      ) : null}
    </article>
  )
}
