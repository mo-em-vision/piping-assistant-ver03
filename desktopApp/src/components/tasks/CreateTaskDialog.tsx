import { useEffect, useMemo, useRef, useState } from 'react'

import type { TaskSummary } from '@/types/frontend/workspace'

import './CreateTaskDialog.css'

const STRAIGHT_PIPE_TASK_CONFIRMATION =
  'Is the pipe wall thickness you would like to calculate for a straight section of pipe? Non-straight sections (fittings, bends) are not yet supported.'

const MAWP_STRAIGHT_PIPE_CONFIRMATION =
  'Is the MAWP calculation for a straight section of pipe? Non-straight sections (fittings, bends) are not yet supported.'

interface CreateTaskDialogProps {
  open: boolean
  tasks: TaskSummary[]
  preselectedWorkflowId?: string
  busy?: boolean
  onSelect: (workflowId: string) => void
  onCancel: () => void
}

export function CreateTaskDialog({
  open,
  tasks,
  preselectedWorkflowId,
  busy = false,
  onSelect,
  onCancel,
}: CreateTaskDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (open) {
      if (preselectedWorkflowId) {
        const match = tasks.find((task) => task.id === preselectedWorkflowId)
        setQuery(match?.name ?? preselectedWorkflowId.replace(/_/g, ' '))
      } else {
        setQuery('')
      }
      if (!dialog.open) {
        dialog.showModal()
      }
      return
    }
    if (dialog.open) {
      dialog.close()
    }
  }, [open, preselectedWorkflowId, tasks])

  const filteredTasks = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return tasks
    }
    return tasks.filter((task) => {
      const haystack = `${task.name} ${task.description} ${task.discipline}`.toLowerCase()
      return haystack.includes(normalized)
    })
  }, [query, tasks])

  const handleSelect = (workflowId: string) => {
    if (workflowId === 'pipe_wall_thickness_design') {
      const confirmed = window.confirm(STRAIGHT_PIPE_TASK_CONFIRMATION)
      if (!confirmed) {
        return
      }
    }
    if (workflowId === 'mawp_design') {
      const confirmed = window.confirm(MAWP_STRAIGHT_PIPE_CONFIRMATION)
      if (!confirmed) {
        return
      }
    }
    onSelect(workflowId)
  }

  if (!open) {
    return null
  }

  return (
    <dialog ref={dialogRef} className="create-task-dialog" onCancel={onCancel}>
      <div className="create-task-dialog__panel">
        <h3 className="create-task-dialog__title">Create new task</h3>
        <input
          className="create-task-dialog__search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search workflows…"
          autoFocus
          disabled={busy}
        />
        <ul className="create-task-dialog__list" role="listbox" aria-label="Available workflows">
          {filteredTasks.length === 0 ? (
            <li className="create-task-dialog__empty">No workflows match your search.</li>
          ) : (
            filteredTasks.map((task) => (
              <li key={task.id}>
                <button
                  type="button"
                  className={`create-task-dialog__item${
                    task.id === preselectedWorkflowId ? ' create-task-dialog__item--highlighted' : ''
                  }`}
                  disabled={busy}
                  onClick={() => handleSelect(task.id)}
                >
                  <span className="create-task-dialog__item-name">{task.name}</span>
                  <span className="create-task-dialog__item-meta">{task.description}</span>
                </button>
              </li>
            ))
          )}
        </ul>
        <div className="create-task-dialog__actions">
          <button type="button" className="create-task-dialog__button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </div>
    </dialog>
  )
}
