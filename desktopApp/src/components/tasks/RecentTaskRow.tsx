import type { MouseEvent } from 'react'

import { SidePanelRowActions } from '@/components/layout/SidePanelRowActions'
import type { TaskSummary } from '@/types/frontend/workspace'

import './RecentTaskRow.css'

interface RecentTaskRowProps {
  task: TaskSummary
  isActive: boolean
  disabled?: boolean
  onSelect: () => void
  onDelete: () => void
  onRename: (task: TaskSummary) => void
  onContextMenu: (event: MouseEvent, task: TaskSummary) => void
}

function formatStatus(status?: string): string {
  if (!status) {
    return 'in progress'
  }
  return status.replace(/_/g, ' ')
}

export function RecentTaskRow({
  task,
  isActive,
  disabled,
  onSelect,
  onDelete,
  onRename,
  onContextMenu,
}: RecentTaskRowProps) {
  return (
    <div
      className={`recent-task-row${isActive ? ' recent-task-row--active' : ''}`}
      onContextMenu={(event) => onContextMenu(event, task)}
    >
      <button
        type="button"
        className="recent-task-row__select"
        disabled={disabled}
        onClick={onSelect}
      >
        <span className="recent-task-row__name">{task.name}</span>
        <span className="recent-task-row__status">{formatStatus(task.status)}</span>
      </button>
      <SidePanelRowActions
        disabled={disabled}
        editLabel={`Rename ${task.name}`}
        deleteLabel={`Delete ${task.name}`}
        onEdit={() => onRename(task)}
        onDelete={onDelete}
      />
    </div>
  )
}
