import type { TimelineStepStatus } from '@/types/frontend/taskState'
import type { NodeProvenanceDto } from '@/types/backend/api'

import { DevNodeHoverSurface } from '@/components/dev/DevNodeHoverSurface'

import './TimelineStep.css'

function stepIcon(status: TimelineStepStatus): string {
  switch (status) {
    case 'done':
      return '✓'
    case 'active':
      return '→'
    default:
      return '○'
  }
}

interface TimelineStepProps {
  title: string
  status: TimelineStepStatus
  displayValue?: string | null
  hint?: string | null
  isLast?: boolean
  editable?: boolean
  onEdit?: () => void
  provenance?: NodeProvenanceDto | null
}

export function TimelineStep({
  title,
  status,
  displayValue,
  hint,
  isLast = false,
  editable = false,
  onEdit,
  provenance,
}: TimelineStepProps) {
  const valueProvenance =
    provenance && displayValue ? { ...provenance, source_field: 'input_id' } : null

  return (
    <div className={`timeline-step timeline-step--${status}${isLast ? ' timeline-step--last' : ''}`}>
      <div className="timeline-step__track">
        <span className="timeline-step__icon" aria-hidden="true">
          {stepIcon(status)}
        </span>
        {!isLast ? <span className="timeline-step__line" aria-hidden="true" /> : null}
      </div>
      <div className="timeline-step__content">
        <div className="timeline-step__title-row">
          <DevNodeHoverSurface provenance={provenance}>
            <span className="timeline-step__title">{title}</span>
          </DevNodeHoverSurface>
          {displayValue ? (
            <DevNodeHoverSurface provenance={valueProvenance}>
              <span className="timeline-step__value">{displayValue}</span>
            </DevNodeHoverSurface>
          ) : null}
          {editable && onEdit ? (
            <button
              type="button"
              className="timeline-step__edit"
              aria-label={`Edit ${title}`}
              title={`Edit ${title}`}
              onClick={onEdit}
            >
              ✎
            </button>
          ) : null}
        </div>
        {hint ? (
          <DevNodeHoverSurface provenance={provenance}>
            <p className="timeline-step__hint">{hint}</p>
          </DevNodeHoverSurface>
        ) : null}
      </div>
    </div>
  )
}
