import type { TimelineStepStatus } from '@/types/frontend/taskState'

import './TimelineStep.css'

function stepIcon(status: TimelineStepStatus): string {
  switch (status) {
    case 'done':
      return '✓'
    case 'active':
      return '→'
    default:
      return '○'
  }
}

interface TimelineStepProps {
  title: string
  status: TimelineStepStatus
  displayValue?: string | null
  hint?: string | null
  isLast?: boolean
}

export function TimelineStep({ title, status, displayValue, hint, isLast = false }: TimelineStepProps) {
  return (
    <div className={`timeline-step timeline-step--${status}${isLast ? ' timeline-step--last' : ''}`}>
      <div className="timeline-step__track">
        <span className="timeline-step__icon" aria-hidden="true">
          {stepIcon(status)}
        </span>
        {!isLast ? <span className="timeline-step__line" aria-hidden="true" /> : null}
      </div>
      <div className="timeline-step__content">
        <div className="timeline-step__title-row">
          <span className="timeline-step__title">{title}</span>
          {displayValue ? <span className="timeline-step__value">{displayValue}</span> : null}
        </div>
        {hint ? <p className="timeline-step__hint">{hint}</p> : null}
      </div>
    </div>
  )
}
