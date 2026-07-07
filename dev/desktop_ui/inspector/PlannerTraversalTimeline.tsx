import type { PlannerTraversalPathRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

const STATE_ICONS: Record<string, string> = {
  completed: '✓',
  current: '●',
  pending: '○',
  blocked: '🔒',
  skipped: '—',
}

type PlannerTraversalTimelineProps = {
  rows: PlannerTraversalPathRowDto[]
  supportLevel?: string | null
  supportNote?: string | null
}

export function PlannerTraversalTimeline({
  rows,
  supportLevel,
  supportNote,
}: PlannerTraversalTimelineProps) {
  const limitedSupport = supportLevel && supportLevel !== 'full'

  if (!rows.length) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Traversal path</h3>
        <p className="inspector-empty">
          {supportNote ??
            'No traversal path rows are available for this workflow snapshot.'}
        </p>
        {limitedSupport ? (
          <p className="inspector-support-note">
            Traversal timeline support: <strong>{supportLevel}</strong> (pipe wall only today).
          </p>
        ) : null}
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Traversal path</h3>
      {limitedSupport && supportNote ? (
        <p className="inspector-support-note">{supportNote}</p>
      ) : null}
      <ol className="inspector-timeline">
        {rows.map((row) => (
          <li
            key={`${row.node_id}-${row.state}`}
            className={`inspector-timeline__row inspector-timeline__row--${row.state}`}
          >
            <span className="inspector-timeline__icon" aria-hidden>
              {STATE_ICONS[row.state] ?? '·'}
            </span>
            <div className="inspector-timeline__content">
              <div className="inspector-timeline__header">
                <strong>{row.title ?? row.node_id}</strong>
                {row.node_type ? (
                  <span className="inspector-rationale-meta"> · {row.node_type}</span>
                ) : null}
              </div>
              <p className="inspector-rationale-meta">{row.node_id}</p>
              {row.reason ? <p className="inspector-timeline__reason">{row.reason}</p> : null}
              {row.waiting_on.length ? (
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
