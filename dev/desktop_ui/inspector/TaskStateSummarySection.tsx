import type { TaskInspectorSummaryDto } from '@/types/backend/inspection'

import { formatNavigationPhase } from './workflowInspectorLabels'

import './InspectorPanels.css'

export function SummarySection({ summary }: { summary: TaskInspectorSummaryDto }) {
  return (
    <div className="inspector-workflow-status">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Task status</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Status</dt>
            <dd className="inspector-status-highlight">{summary.status ?? '—'}</dd>
          </div>
          <div>
            <dt>Phase</dt>
            <dd>{formatNavigationPhase(summary.phase ?? null)}</dd>
          </div>
          {summary.current_blocker ? (
            <div>
              <dt>Blocker</dt>
              <dd>
                {summary.current_blocker.type}
                {summary.current_blocker.field ? ` · ${summary.current_blocker.field}` : ''}
              </dd>
            </div>
          ) : null}
        </dl>
      </section>

      {summary.missing_inputs.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Missing inputs</h3>
          <div className="inspector-node-chips">
            {summary.missing_inputs.map((field) => (
              <span key={field} className="inspector-node-chip inspector-node-chip--pending">
                {field}
              </span>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
