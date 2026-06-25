import type { TaskSummary } from '@/types/frontend/workspace'

import './RecentTaskRow.css'

interface RecentTaskRowProps {
  task: TaskSummary
  isActive: boolean
  disabled?: boolean
  onSelect: () => void
  onDelete: () => void
}

function formatStatus(status?: string): string {
  if (!status) {
    return 'in progress'
  }
  return status.replace(/_/g, ' ')
}

export function RecentTaskRow({ task, isActive, disabled, onSelect, onDelete }: RecentTaskRowProps) {
  return (
    <div className={`recent-task-row${isActive ? ' recent-task-row--active' : ''}`}>
      <button
        type="button"
        className="recent-task-row__select"
        disabled={disabled}
        onClick={onSelect}
      >
        <span className="recent-task-row__name">{task.name}</span>
        <span className="recent-task-row__status">{formatStatus(task.status)}</span>
      </button>
      <button
        type="button"
        className="recent-task-row__delete"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation()
          onDelete()
        }}
        aria-label={`Delete ${task.name}`}
        title="Delete task"
      >
        🗑
      </button>
    </div>
  )
}
