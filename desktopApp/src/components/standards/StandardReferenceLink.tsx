import {
  useRightPanelStore,
  type NodeViewerContext,
  type StandardsReferenceKind,
  type TableViewerContext,
} from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { buildTableViewerContext } from '@/utils/tableViewerContext'

import './StandardReferenceLink.css'

export type StandardReferenceLinkVariant = 'inline' | 'chip'

interface StandardReferenceLinkProps {
  referenceKind?: StandardsReferenceKind
  referenceId?: string
  subsectionId?: string
  nodeId?: string
  label: string
  viewerContext?: TableViewerContext | NodeViewerContext
  /** When false, open the reference tab without leaving the current panel view. */
  activateTab?: boolean
  variant?: StandardReferenceLinkVariant
}

export function StandardReferenceLink({
  referenceKind = 'node',
  referenceId,
  subsectionId,
  nodeId,
  label,
  viewerContext,
  activateTab = true,
  variant = 'inline',
}: StandardReferenceLinkProps) {
  const resolvedId = referenceId ?? nodeId ?? ''
  const openReferenceTab = useRightPanelStore((state) => state.openReferenceTab)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)

  const resolvedViewerContext =
    viewerContext ??
    (referenceKind === 'table'
      ? buildTableViewerContext(resolvedId, activeTaskState)
      : subsectionId
        ? { subsectionId }
        : undefined)

  const buttonClass =
    variant === 'chip'
      ? 'standard-reference-link__button standard-reference-link__button--chip'
      : 'standard-reference-link__button standard-reference-link__button--inline'

  return (
    <span className="standard-reference-link">
      <button
        type="button"
        className={buttonClass}
        onClick={() => {
          useUiStore.setState({ rightCollapsed: false })
          openReferenceTab(resolvedId, label, referenceKind, resolvedViewerContext, {
            activate: activateTab,
          })
        }}
      >
        {label}
      </button>
    </span>
  )
}
