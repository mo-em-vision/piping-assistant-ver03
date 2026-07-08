import './WorkflowHeader.css'

interface WorkflowHeaderProps {
  taskName: string
  subtitle?: string | null
  onDelete?: () => void
  deleteDisabled?: boolean
}

export function WorkflowHeader({
  taskName,
  subtitle,
  onDelete,
  deleteDisabled,
}: WorkflowHeaderProps) {
  return (
    <header className="workflow-header">
      <div className="workflow-header__top">
        <div className="workflow-header__titles">
          <h2 className="workflow-header__title">{taskName}</h2>
          {subtitle ? <p className="workflow-header__subtitle">{subtitle}</p> : null}
        </div>
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
