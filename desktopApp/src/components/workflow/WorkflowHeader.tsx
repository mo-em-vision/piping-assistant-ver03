import './WorkflowHeader.css'

interface WorkflowHeaderProps {
  taskName: string
  onDelete?: () => void
  deleteDisabled?: boolean
}

export function WorkflowHeader({
  taskName,
  onDelete,
  deleteDisabled,
}: WorkflowHeaderProps) {
  return (
    <header className="workflow-header">
      <div className="workflow-header__top">
        <h2 className="workflow-header__title">{taskName}</h2>
        {onDelete ? (
          <button
            type="button"
            className="workflow-header__delete"
            onClick={onDelete}
            disabled={deleteDisabled}
            aria-label={`Delete ${taskName}`}
          >
            Delete task
          </button>
        ) : null}
      </div>
    </header>
  )
}
