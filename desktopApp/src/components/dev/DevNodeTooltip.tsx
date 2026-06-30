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

export function DevNodeTooltip({
  provenance,
  x,
  y,
  onOpenEdit,
  onMouseEnter,
  onMouseLeave,
}: DevNodeTooltipProps) {
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
      <p className="dev-node-tooltip__id">{provenance.node_id}</p>
      <p className="dev-node-tooltip__field">{sourceField}</p>
    </button>
  )
}
