import './TaskProgress.css'

interface TaskProgressProps {
  percent: number
  completedCount: number
  totalCount: number
}

export function TaskProgress({ percent, completedCount, totalCount }: TaskProgressProps) {
  return (
    <div className="task-progress">
      <div className="task-progress__header">
        <span className="task-progress__label">Progress</span>
        <span className="task-progress__count">
          {completedCount}/{totalCount} steps
        </span>
      </div>
      <div
        className="task-progress__bar"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Task progress ${percent}%`}
      >
        <div className="task-progress__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
