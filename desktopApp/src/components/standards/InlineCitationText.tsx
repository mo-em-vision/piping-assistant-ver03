import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import type { StandardsReferenceKind } from '@/store/rightPanelStore'
import type { ReferenceChipDto, ReferenceLinkDto } from '@/types/backend/outputs'

export interface InlineCitationLinkProps {
  referenceKind?: StandardsReferenceKind
  referenceId: string
  label: string
  activateTab?: boolean
}

interface InlineCitationTextProps {
  /** Plain prefix before the linked citation (e.g. "Resolved from"). */
  prefix?: string
  /** Full provenance or sentence label; may already embed the citation for legacy payloads. */
  label?: string
  /** Linkable citation text when known separately from prefix. */
  linkLabel?: string
  chip?: ReferenceChipDto
  link?: ReferenceLinkDto
  detail?: string
  className?: string
}

function chipReferenceKind(chip: ReferenceChipDto): StandardsReferenceKind {
  return chip.ref_type === 'table' ? 'table' : 'node'
}

function chipReferenceId(chip: ReferenceChipDto): string {
  return (
    chip.target.node_id ??
    chip.target.equation_id ??
    chip.target.table_id ??
    chip.target.paragraph_id ??
    chip.id
  )
}

function linkReferenceKind(link: ReferenceLinkDto): StandardsReferenceKind {
  return link.reference_kind === 'table' ? 'table' : 'node'
}

/**
 * Split a legacy combined label like "Resolved from Table A-1" into prefix + citation.
 */
export function splitCitationLabel(
  combinedLabel: string,
  citationLabel: string,
): { prefix: string; citation: string } {
  const combined = combinedLabel.trim()
  const citation = citationLabel.trim()
  if (!citation) {
    return { prefix: combined, citation: '' }
  }
  if (combined === citation) {
    return { prefix: '', citation }
  }
  if (combined.endsWith(citation)) {
    const prefix = combined.slice(0, combined.length - citation.length).trimEnd()
    return { prefix, citation }
  }
  const lowerCombined = combined.toLowerCase()
  const lowerCitation = citation.toLowerCase()
  const index = lowerCombined.lastIndexOf(lowerCitation)
  if (index >= 0) {
    return {
      prefix: combined.slice(0, index).trimEnd(),
      citation: combined.slice(index).trim(),
    }
  }
  return { prefix: combined, citation }
}

function renderInlineLink({
  referenceKind,
  referenceId,
  label,
  activateTab,
}: InlineCitationLinkProps) {
  return (
    <StandardReferenceLink
      referenceKind={referenceKind}
      referenceId={referenceId}
      nodeId={referenceId}
      label={label}
      activateTab={activateTab}
      variant="inline"
    />
  )
}

export function InlineCitationText({
  prefix,
  label,
  linkLabel,
  chip,
  link,
  detail,
  className,
}: InlineCitationTextProps) {
  const resolvedLinkLabel = linkLabel ?? chip?.label ?? link?.label ?? ''
  const resolvedReferenceId = chip
    ? chipReferenceId(chip)
    : link?.node_id ?? ''
  const resolvedReferenceKind = chip
    ? chipReferenceKind(chip)
    : link
      ? linkReferenceKind(link)
      : 'node'

  let resolvedPrefix = prefix ?? ''
  let citation = resolvedLinkLabel

  if (!citation && label) {
    return (
      <span className={className}>
        {label}
        {detail ? <span className="inline-citation-text__detail"> {detail}</span> : null}
      </span>
    )
  }

  if (!resolvedPrefix && label && citation) {
    const split = splitCitationLabel(label, citation)
    resolvedPrefix = split.prefix
    citation = split.citation || citation
  } else if (!resolvedPrefix && label && !citation) {
    return (
      <span className={className}>
        {label}
        {detail ? <span className="inline-citation-text__detail"> {detail}</span> : null}
      </span>
    )
  }

  const hasLink = Boolean(resolvedReferenceId && citation)

  return (
    <span className={className}>
      {resolvedPrefix ? <>{resolvedPrefix} </> : null}
      {hasLink ? (
        renderInlineLink({
          referenceKind: resolvedReferenceKind,
          referenceId: resolvedReferenceId,
          label: citation,
        })
      ) : (
        citation
      )}
      {detail ? <span className="inline-citation-text__detail"> {detail}</span> : null}
    </span>
  )
}

interface InlineCitationListProps {
  prefix?: string
  chips: ReferenceChipDto[]
  className?: string
}

/** Comma-separated inline citations (e.g. chat Sources line). */
export function InlineCitationList({ prefix, chips, className }: InlineCitationListProps) {
  if (!chips.length) {
    return null
  }

  return (
    <span className={className}>
      {prefix ? <>{prefix} </> : null}
      {chips.map((chip, index) => (
        <span key={`${chip.ref_type}:${chip.id}`}>
          {index > 0 ? ', ' : null}
          {renderInlineLink({
            referenceKind: chipReferenceKind(chip),
            referenceId: chipReferenceId(chip),
            label: chip.label,
          })}
        </span>
      ))}
    </span>
  )
}
