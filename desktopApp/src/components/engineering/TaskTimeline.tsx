import { TimelineStep } from './TimelineStep'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

import './TaskTimeline.css'

interface TaskTimelineProps {
  steps: TimelineStepViewModel[]
  emptyMessage?: string
}

export function TaskTimeline({ steps, emptyMessage = 'No progress information yet.' }: TaskTimelineProps) {
  if (steps.length === 0) {
    return <p className="task-timeline__empty">{emptyMessage}</p>
  }

  return (
    <div className="task-timeline" role="list" aria-label="Task progress timeline">
      {steps.map((step, index) => (
        <div key={step.id} role="listitem">
          <TimelineStep
            title={step.title}
            status={step.status}
            displayValue={step.displayValue}
            hint={step.hint}
            isLast={index === steps.length - 1}
          />
        </div>
      ))}
    </div>
  )
}
