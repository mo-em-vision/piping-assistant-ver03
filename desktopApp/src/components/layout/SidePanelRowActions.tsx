import './SidePanelRowActions.css'

interface SidePanelRowActionsProps {
  disabled?: boolean
  editLabel: string
  deleteLabel: string
  onEdit: () => void
  onDelete: () => void
}

export function SidePanelRowActions({
  disabled,
  editLabel,
  deleteLabel,
  onEdit,
  onDelete,
}: SidePanelRowActionsProps) {
  return (
    <div className="side-panel-row-actions">
      <button
        type="button"
        className="side-panel-row-actions__edit"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation()
          onEdit()
        }}
        aria-label={editLabel}
        title={editLabel}
      >
        ✎
      </button>
      <button
        type="button"
        className="side-panel-row-actions__delete"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation()
          onDelete()
        }}
        aria-label={deleteLabel}
        title={deleteLabel}
      >
        ×
      </button>
    </div>
  )
}
