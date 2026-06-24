import { useEffect, useRef } from 'react'

import type { TaskSummary } from '@/types/frontend/workspace'

import './TaskContextMenu.css'

interface TaskContextMenuProps {
  task: TaskSummary
  x: number
  y: number
  onDelete: (task: TaskSummary) => void
  onClose: () => void
}

export function TaskContextMenu({ task, x, y, onDelete, onClose }: TaskContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current?.contains(event.target as Node)) {
        return
      }
      onClose()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    const handleScroll = () => {
      onClose()
    }

    window.addEventListener('mousedown', handlePointerDown)
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('scroll', handleScroll, true)

    return () => {
      window.removeEventListener('mousedown', handlePointerDown)
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [onClose])

  return (
    <div
      ref={menuRef}
      className="task-context-menu"
      style={{ top: y, left: x }}
      role="menu"
      aria-label={`Actions for ${task.name}`}
    >
      <button
        type="button"
        className="task-context-menu__item task-context-menu__item--danger"
        role="menuitem"
        onClick={() => {
          onDelete(task)
          onClose()
        }}
      >
        Delete task
      </button>
    </div>
  )
}
