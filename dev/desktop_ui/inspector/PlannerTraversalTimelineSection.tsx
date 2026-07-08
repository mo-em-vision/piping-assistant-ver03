import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

const STATE_ICONS: Record<string, string> = {
  visited: '✓',
  active: '●',
  pending: '○',
  blocked: '🔒',
  skipped: '—',
}

type PlannerTraversalTimelineSectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerTraversalTimelineSection({ projection }: PlannerTraversalTimelineSectionProps) {
  const rows = projection.visited_timeline ?? []

  if (!rows.length) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Traversal Timeline</h3>
        <p className="inspector-empty">not available</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Traversal Timeline</h3>
      <ol className="inspector-timeline">
        {rows.map((row) => (
          <li
            key={`${row.node_id}-${row.status}`}
            className={`inspector-timeline__row inspector-timeline__row--${row.status}`}
          >
            <span className="inspector-timeline__icon" aria-hidden>
              {STATE_ICONS[row.status] ?? '·'}
            </span>
            <div className="inspector-timeline__content">
              <div className="inspector-timeline__header">
                <strong>{row.title ?? row.node_id}</strong>
                {row.node_type ? (
                  <span className="inspector-rationale-meta"> · {row.node_type}</span>
                ) : null}
                <span className="inspector-rationale-meta"> · {row.status}</span>
              </div>
              <p className="inspector-rationale-meta">{row.node_id}</p>
              {row.why_visited ? (
                <p className="inspector-timeline__reason">{row.why_visited}</p>
              ) : null}
              {row.waiting_on?.length ? (
                <p className="inspector-timeline__waiting">
                  Waiting on: {row.waiting_on.join(', ')}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
