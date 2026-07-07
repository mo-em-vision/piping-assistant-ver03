import type { ExpansionTimelinePhase } from '../types'

interface ExpansionTimelinePanelProps {
  timeline: ExpansionTimelinePhase[]
  currentPhase: string
}

function formatLabel(value: string): string {
  return value.replace(/_/g, ' ')
}

export default function ExpansionTimelinePanel({ timeline, currentPhase }: ExpansionTimelinePanelProps) {
  if (!timeline.length) return null

  return (
    <div className="expansion-timeline">
      <div className="section-title">Expansion timeline</div>
      {timeline.map((phase) => (
        <div
          key={phase.phase}
          className={`expansion-timeline__phase ${phase.phase === currentPhase ? 'is-current' : ''}`}
        >
          <div className="expansion-timeline__phase-title">
            {formatLabel(phase.phase)}
            <span className={`expansion-timeline__phase-status status-${phase.status}`}>
              {formatLabel(phase.status)}
            </span>
          </div>
          <ul className="expansion-timeline__items">
            {phase.items.map((item) => (
              <li key={item.id} className={`expansion-timeline__item status-${item.status}`}>
                <span>{formatLabel(item.id)}</span>
                <span className="expansion-timeline__item-status">{formatLabel(item.status)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
