import { DevNodeHoverSurface } from '@dev-ui/DevNodeHoverSurface'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'

import type { ActiveNodeContextDto } from '@/types/backend/api'
import { activeContextToProvenance } from '@/utils/nodeProvenance'

import './WorkflowHeader.css'

interface WorkflowHeaderProps {
  taskName: string
  context: ActiveNodeContextDto | null | undefined
  onDelete?: () => void
  deleteDisabled?: boolean
}

function renderHeading(context: ActiveNodeContextDto) {
  const provenance = activeContextToProvenance(context)
  const heading = context.display_heading
  const match = heading.match(/^(.*?)(\s*\(according to (.+)\)\s*)$/i)

  if (!match) {
    return (
      <DevNodeHoverSurface provenance={provenance}>
        <p className="workflow-header__heading">{heading}</p>
      </DevNodeHoverSurface>
    )
  }

  const lead = match[1].trim()
  const referenceLabel = match[3].trim()

  return (
    <DevNodeHoverSurface provenance={provenance}>
      <p className="workflow-header__heading">
        {lead} (according to{' '}
        <StandardReferenceLink nodeId={context.node_id} label={referenceLabel} provenance={provenance} />
        )
      </p>
    </DevNodeHoverSurface>
  )
}

export function WorkflowHeader({
  taskName,
  context,
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
      {context ? renderHeading(context) : null}
    </header>
  )
}
