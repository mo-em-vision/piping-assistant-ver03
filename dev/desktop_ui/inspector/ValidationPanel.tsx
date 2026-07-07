import type { TaskValidationViewDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type ValidationPanelProps = {
  view: TaskValidationViewDto
}

export function ValidationPanel({ view }: ValidationPanelProps) {
  const hasContent =
    view.errors.length || view.warnings.length || view.conflicts.length || view.overrides.length

  if (!hasContent) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Validation</h3>
        <p className="inspector-rationale-meta">No validation issues.</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Validation and warnings</h3>
      <p className="inspector-rationale-meta">
        Status: <span className={`inspector-badge inspector-badge--${view.status}`}>{view.status}</span>
      </p>
      {view.errors.length ? (
        <div>
          <h4 className="inspector-requirements-group__title">Errors</h4>
          <ul className="inspector-warning-list">
            {view.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {view.warnings.length ? (
        <div>
          <h4 className="inspector-requirements-group__title">Warnings</h4>
          <ul className="inspector-warning-list">
            {view.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {view.conflicts.length ? (
        <div>
          <h4 className="inspector-requirements-group__title">Conflicts</h4>
          <ul className="inspector-missing-list">
            {view.conflicts.map((conflict) => (
              <li key={conflict.field}>
                <strong>{conflict.field}</strong>: {conflict.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {view.affected_nodes.length ? (
        <div>
          <h4 className="inspector-requirements-group__title">Affected nodes</h4>
          <div className="inspector-node-chips">
            {view.affected_nodes.map((nodeId) => (
              <span key={nodeId} className="inspector-node-chip">
                {nodeId}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
