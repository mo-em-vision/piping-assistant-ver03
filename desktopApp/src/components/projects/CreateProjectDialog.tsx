import { useEffect, useRef, useState, type FormEvent } from 'react'

import './CreateProjectDialog.css'

interface CreateProjectDialogProps {
  open: boolean
  busy?: boolean
  onConfirm: (name: string) => void
  onCancel: () => void
}

export function CreateProjectDialog({ open, busy = false, onConfirm, onCancel }: CreateProjectDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState('')

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (open) {
      setName('')
      if (!dialog.open) {
        dialog.showModal()
      }
      return
    }
    if (dialog.open) {
      dialog.close()
    }
  }, [open])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      return
    }
    onConfirm(trimmed)
  }

  if (!open) {
    return null
  }

  return (
    <dialog ref={dialogRef} className="create-project-dialog" onCancel={onCancel}>
      <form method="dialog" className="create-project-dialog__panel" onSubmit={handleSubmit}>
        <h3 className="create-project-dialog__title">Create new project</h3>
        <label className="create-project-dialog__label" htmlFor="project-name">
          Project name
        </label>
        <input
          id="project-name"
          className="create-project-dialog__input"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Refinery Expansion"
          autoFocus
          disabled={busy}
        />
        <div className="create-project-dialog__actions">
          <button type="button" className="create-project-dialog__button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            type="submit"
            className="create-project-dialog__button create-project-dialog__button--primary"
            disabled={busy || !name.trim()}
          >
            {busy ? 'Creating…' : 'Create project'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
