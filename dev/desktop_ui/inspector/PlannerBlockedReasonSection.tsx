import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import { displayValue } from './plannerDebugDisplay'

import './InspectorPanels.css'

const KIND_LABELS: Record<string, string> = {
  waiting_for_user_input: 'Waiting for user input',
  waiting_for_equation_dependency: 'Waiting for equation dependency',
  waiting_for_lookup_resolution: 'Waiting for lookup resolution',
  blocked_by_validation: 'Blocked by validation',
  complete: 'Complete',
  not_available: 'Not available',
}

type PlannerBlockedReasonSectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerBlockedReasonSection({ projection }: PlannerBlockedReasonSectionProps) {
  const blocked = projection.blocked_reason
  const kind = blocked?.kind ?? 'not_available'
  const kindLabel = KIND_LABELS[kind] ?? displayValue(kind)

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Blocked / Waiting Reason</h3>
      <div className="inspector-card">
        <span className={`inspector-badge inspector-badge--${kind}`}>{kindLabel}</span>
        <dl className="inspector-status-grid">
          <div>
            <dt>Message</dt>
            <dd>{displayValue(blocked?.message)}</dd>
          </div>
          <div>
            <dt>Missing item</dt>
            <dd className="inspector-status-highlight">{displayValue(blocked?.missing_item)}</dd>
          </div>
        </dl>
      </div>
      {projection.warnings?.length ? (
        <div className="inspector-phase-block">
          <p className="inspector-phase-block__label">Plan warnings</p>
          <ul className="inspector-warning-list">
            {projection.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
