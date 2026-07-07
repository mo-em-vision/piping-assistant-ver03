import type { TraceTimelineRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type TraceTimelinePanelProps = {
  rows: TraceTimelineRowDto[]
}

export function TraceTimelinePanel({ rows }: TraceTimelinePanelProps) {
  if (!rows.length) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Event timeline</h3>
        <p className="inspector-empty">No execution or lifecycle events yet.</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Event timeline</h3>
      <ol className="inspector-timeline inspector-timeline--events">
        {rows.map((row) => (
          <li key={`${row.source}-${row.order}-${row.event_type}`} className="inspector-timeline__row">
            <span className="inspector-timeline__order">#{row.order}</span>
            <div className="inspector-timeline__content">
              <div className="inspector-timeline__header">
                <strong>{row.label}</strong>
                <span className="inspector-rationale-meta"> · {row.source}</span>
              </div>
              {row.node_id ? <p className="inspector-rationale-meta">{row.node_id}</p> : null}
              {row.message ? <p className="inspector-timeline__reason">{row.message}</p> : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
