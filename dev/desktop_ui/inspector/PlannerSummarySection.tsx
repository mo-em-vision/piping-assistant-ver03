import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import { displayValue } from './plannerDebugDisplay'

import './InspectorPanels.css'

const STATUS_LABELS: Record<string, string> = {
  waiting_for_input: 'Waiting for input',
  ready: 'Ready',
  blocked: 'Blocked',
  executing: 'Executing',
  completed: 'Completed',
  invalidated: 'Invalidated',
}

type PlannerSummarySectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerSummarySection({ projection }: PlannerSummarySectionProps) {
  const statusBadge = projection.current_step?.status_badge ?? ''
  const statusLabel = STATUS_LABELS[statusBadge] ?? displayValue(statusBadge)

  return (
    <section className="inspector-card inspector-card--planner">
      <h3 className="inspector-workflow-status__title">Planner Summary</h3>
      <div className="inspector-card__header">
        <p className="inspector-card__title">{displayValue(projection.workflow_title)}</p>
        <span className={`inspector-badge inspector-badge--${statusBadge || 'blocked'}`}>
          {statusLabel}
        </span>
      </div>
      <dl className="inspector-status-grid">
        <div>
          <dt>Workflow slug</dt>
          <dd>{displayValue(projection.workflow_slug)}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>
            {projection.planner_confidence === null || projection.planner_confidence === undefined
              ? displayValue(null)
              : projection.planner_confidence}
          </dd>
        </div>
        <div>
          <dt>Selection reason</dt>
          <dd>{displayValue(projection.planner_reason)}</dd>
        </div>
        <div>
          <dt>Current phase</dt>
          <dd>{displayValue(projection.current_step?.phase_label)}</dd>
        </div>
      </dl>
    </section>
  )
}
