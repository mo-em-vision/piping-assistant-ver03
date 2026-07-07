import type { TaskStateSummaryDto } from '@/types/backend/inspection'

import { formatNavigationPhase } from './workflowInspectorLabels'

import './InspectorPanels.css'

const READINESS_LABELS: Record<string, string> = {
  in_progress: 'In progress',
  waiting_for_input: 'Waiting for input',
  ready: 'Ready',
  completed: 'Completed',
  invalidated: 'Invalidated',
}

type TaskStateHeaderCardProps = {
  summary: TaskStateSummaryDto
}

export function TaskStateHeaderCard({ summary }: TaskStateHeaderCardProps) {
  const readinessLabel = READINESS_LABELS[summary.readiness] ?? summary.readiness

  return (
    <section className="inspector-card">
      <div className="inspector-card__header">
        <h3 className="inspector-card__title">{summary.task_name ?? summary.task_id}</h3>
        <span className={`inspector-badge inspector-badge--${summary.readiness}`}>{readinessLabel}</span>
      </div>
      <dl className="inspector-status-grid">
        <div>
          <dt>Task status</dt>
          <dd className="inspector-status-highlight">{summary.status}</dd>
        </div>
        <div>
          <dt>Workflow</dt>
          <dd>{summary.workflow_id || '—'}</dd>
        </div>
        <div>
          <dt>Selected root</dt>
          <dd>{summary.selected_root || '—'}</dd>
        </div>
        <div>
          <dt>Current phase</dt>
          <dd>{formatNavigationPhase(summary.current_phase)}</dd>
        </div>
        <div>
          <dt>Missing inputs</dt>
          <dd>{summary.missing_input_count}</dd>
        </div>
      </dl>
    </section>
  )
}
