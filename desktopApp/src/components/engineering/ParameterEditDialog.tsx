import { useEffect, useRef } from 'react'

import type { ParameterEditImpactDto } from '@/types/backend/api'

import './ParameterEditDialog.css'

interface ParameterEditDialogProps {
  impact: ParameterEditImpactDto | null
  stepTitle: string
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ParameterEditDialog({
  impact,
  stepTitle,
  busy = false,
  onConfirm,
  onCancel,
}: ParameterEditDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (impact) {
      if (!dialog.open) {
        dialog.showModal()
      }
      return
    }
    if (dialog.open) {
      dialog.close()
    }
  }, [impact])

  if (!impact) {
    return null
  }

  return (
    <dialog ref={dialogRef} className="parameter-edit-dialog" onCancel={onCancel}>
      <form method="dialog" className="parameter-edit-dialog__panel">
        <h3 className="parameter-edit-dialog__title">Edit {stepTitle}?</h3>
        {impact.affects_design ? (
          <p className="parameter-edit-dialog__warning">
            {impact.message ??
              'Changing this input may affect the calculation path and clear downstream values.'}
          </p>
        ) : (
          <p className="parameter-edit-dialog__body">
            You can update this value and continue the workflow from this step.
          </p>
        )}
        {impact.affects_path ? (
          <p className="parameter-edit-dialog__note">
            The governing code section or calculation node may change based on this input.
          </p>
        ) : null}
        <div className="parameter-edit-dialog__actions">
          <button type="button" className="parameter-edit-dialog__button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="parameter-edit-dialog__button parameter-edit-dialog__button--primary"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Opening…' : 'Edit value'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
