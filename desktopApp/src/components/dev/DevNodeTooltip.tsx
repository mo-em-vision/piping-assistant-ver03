import type { NodeProvenanceDto } from '@/types/backend/api'

import './DevNodeHover.css'

interface DevNodeTooltipProps {
  provenance: NodeProvenanceDto
  x: number
  y: number
  onOpenEdit: (provenance: NodeProvenanceDto) => void
  onMouseEnter: () => void
  onMouseLeave: () => void
}

function formatMeta(provenance: NodeProvenanceDto): string | null {
  const parts: string[] = []
  if (provenance.standard) {
    parts.push(provenance.standard)
  }
  if (provenance.paragraph) {
    parts.push(`§${provenance.paragraph}`)
  }
  return parts.length > 0 ? parts.join(' · ') : null
}

function truncateExcerpt(text: string, maxLength = 160): string {
  if (text.length <= maxLength) {
    return text
  }
  return `${text.slice(0, maxLength).trimEnd()}…`
}

export function DevNodeTooltip({
  provenance,
  x,
  y,
  onOpenEdit,
  onMouseEnter,
  onMouseLeave,
}: DevNodeTooltipProps) {
  const meta = formatMeta(provenance)
  const offset = 12
  const sourceField = provenance.source_field?.trim() || 'unknown'

  return (
    <button
      type="button"
      className="dev-node-tooltip"
      role="tooltip"
      style={{
        left: Math.max(8, x + offset),
        top: Math.max(8, y + offset),
      }}
      onClick={() => onOpenEdit(provenance)}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <p className="dev-node-tooltip__id">Node: {provenance.node_id}</p>
      <p className="dev-node-tooltip__field">
        Field: <span className="dev-node-tooltip__field-name">{sourceField}</span>
      </p>
      {provenance.title ? <p className="dev-node-tooltip__title">{provenance.title}</p> : null}
      {meta ? <p className="dev-node-tooltip__meta">{meta}</p> : null}
      <p className="dev-node-tooltip__excerpt">{truncateExcerpt(provenance.hover_excerpt)}</p>
      <p className="dev-node-tooltip__hint">Click to edit node</p>
    </button>
  )
}
