import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { EngineeringMathText } from '@/components/math/engineeringMath'
import { ReferenceChipList } from '@/components/outputs/ReferenceChipList'

import type { ReferenceLinkDto } from '@/types/backend/outputs'
import type { TextOutputBlock } from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'

interface TextOutputProps {
  block: TextOutputBlock
}

function ReferenceLinkList({ links }: { links: ReferenceLinkDto[] }) {
  if (!links.length) {
    return null
  }

  return (
    <div className="output-text__references">
      {links.map((link) => (
        <StandardReferenceLink
          key={link.node_id}
          nodeId={link.node_id}
          label={link.label}
        />
      ))}
    </div>
  )
}

function InlineReferenceLinks({ links }: { links: ReferenceLinkDto[] }) {
  if (!links.length) {
    return null
  }

  return (
    <>
      {links.map((link, index) => (
        <span key={link.node_id}>
          {index === 0 ? ' ' : ', '}
          <StandardReferenceLink nodeId={link.node_id} label={link.label} />
        </span>
      ))}
    </>
  )
}

export function TextOutput({ block }: TextOutputProps) {
  const variantClass =
    block.variant === 'warning'
      ? 'output-text output-text--warning'
      : block.variant === 'caption'
        ? 'output-text output-text--caption'
        : block.variant === 'assumption'
          ? 'output-text output-text--assumption'
          : 'output-text'
  const inlineReferences = block.reference_links_placement === 'inline'

  return (
    <article className="output-block">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <p className={variantClass}>
        {block.variant === 'assumption' ? (
          <>
            <strong className="output-text__assumption-label">Assumptions:</strong>{' '}
          </>
        ) : null}
        <EngineeringMathText text={block.content} />
        {inlineReferences ? (
          <ReferenceChipList chips={block.reference_chips} className="reference-chip-list--inline" />
        ) : null}
        {inlineReferences && !block.reference_chips?.length && block.reference_links?.length ? (
          <InlineReferenceLinks links={block.reference_links} />
        ) : null}
        {block.content_suffix ? <EngineeringMathText text={block.content_suffix} /> : null}
      </p>
      {!inlineReferences && block.reference_chips?.length ? (
        <ReferenceChipList chips={block.reference_chips} />
      ) : null}
      {!inlineReferences && !block.reference_chips?.length && block.reference_links?.length ? (
        <ReferenceLinkList links={block.reference_links} />
      ) : null}
    </article>
  )
}
