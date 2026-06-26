import { useEffect, useRef, useState, type FormEvent } from 'react'

import '@/components/projects/CreateProjectDialog.css'

interface RenameDialogProps {
  open: boolean
  title: string
  label: string
  initialName: string
  busy?: boolean
  confirmLabel?: string
  onConfirm: (name: string) => void
  onCancel: () => void
}

export function RenameDialog({
  open,
  title,
  label,
  initialName,
  busy = false,
  confirmLabel = 'Save',
  onConfirm,
  onCancel,
}: RenameDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState(initialName)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (open) {
      setName(initialName)
      if (!dialog.open) {
        dialog.showModal()
      }
      return
    }
    if (dialog.open) {
      dialog.close()
    }
  }, [initialName, open])

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
        <h3 className="create-project-dialog__title">{title}</h3>
        <label className="create-project-dialog__label" htmlFor="rename-input">
          {label}
        </label>
        <input
          id="rename-input"
          className="create-project-dialog__input"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
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
            {busy ? 'Saving…' : confirmLabel}
          </button>
        </div>
      </form>
    </dialog>
  )
}
