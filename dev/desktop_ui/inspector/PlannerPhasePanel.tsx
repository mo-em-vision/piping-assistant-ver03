import type { PlannerPhasePanelDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type PlannerPhasePanelProps = {
  panel: PlannerPhasePanelDto
}

export function PlannerPhasePanel({ panel }: PlannerPhasePanelProps) {
  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Planner phase — {panel.current_phase_label}</h3>

      {panel.active_field ? (
        <div className="inspector-phase-block">
          <p className="inspector-phase-block__label">Active field now</p>
          <p className="inspector-status-highlight">{panel.active_field}</p>
        </div>
      ) : null}

      {panel.completed_fields.length ? (
        <div className="inspector-phase-block">
          <p className="inspector-phase-block__label">Completed in this phase</p>
          <div className="inspector-node-chips">
            {panel.completed_fields.map((item) => (
              <span key={item.field} className="inspector-node-chip">
                {item.label}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {panel.missing_in_phase.length ? (
        <div className="inspector-phase-block">
          <p className="inspector-phase-block__label">Still missing in this phase</p>
          <ul className="inspector-missing-list">
            {panel.missing_in_phase.map((item) => (
              <li key={item.field}>
                <strong>{item.label}</strong>
                <span className="inspector-rationale-meta"> ({item.field})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {panel.future_fields.length ? (
        <div className="inspector-phase-block inspector-phase-block--future">
          <p className="inspector-phase-block__label">Future — not being asked yet</p>
          <ul className="inspector-missing-list">
            {panel.future_fields.map((item) => (
              <li key={item.field}>
                <strong>{item.label}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.field}, {item.phase})
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
