import { TimelineStep } from './TimelineStep'
import type { TimelineStepViewModel } from '@/types/frontend/taskState'

import './TaskTimeline.css'

interface TaskTimelineProps {
  steps: TimelineStepViewModel[]
  emptyMessage?: string
  onEditStep?: (stepId: string) => void
}

export function TaskTimeline({
  steps,
  emptyMessage = 'No progress information yet.',
  onEditStep,
}: TaskTimelineProps) {
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
            editable={step.editable}
            onEdit={step.editable && onEditStep ? () => onEditStep(step.id) : undefined}
          />
        </div>
      ))}
    </div>
  )
}
