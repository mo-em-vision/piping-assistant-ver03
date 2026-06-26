import type { TaskSummary } from '@/types/frontend/workspace'

import { SidePanelContextMenu } from '@/components/layout/SidePanelContextMenu'

import './TaskContextMenu.css'

interface TaskContextMenuProps {
  task: TaskSummary
  x: number
  y: number
  onDelete: (task: TaskSummary) => void
  onClose: () => void
}

export function TaskContextMenu({ task, x, y, onDelete, onClose }: TaskContextMenuProps) {
  return (
    <SidePanelContextMenu
      x={x}
      y={y}
      ariaLabel={`Actions for ${task.name}`}
      onClose={onClose}
      items={[
        {
          label: 'Delete task',
          danger: true,
          onClick: () => onDelete(task),
        },
      ]}
    />
  )
}
