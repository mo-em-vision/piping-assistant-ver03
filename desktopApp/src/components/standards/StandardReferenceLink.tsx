import {
  useRightPanelStore,
  type StandardsReferenceKind,
  type TableViewerContext,
} from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { buildTableViewerContext } from '@/utils/tableViewerContext'

import './StandardReferenceLink.css'

interface StandardReferenceLinkProps {
  referenceKind?: StandardsReferenceKind
  referenceId?: string
  nodeId?: string
  label: string
  viewerContext?: TableViewerContext
  /** When false, open the reference tab without leaving the current panel view. */
  activateTab?: boolean
}

export function StandardReferenceLink({
  referenceKind = 'node',
  referenceId,
  nodeId,
  label,
  viewerContext,
  activateTab = true,
}: StandardReferenceLinkProps) {
  const resolvedId = referenceId ?? nodeId ?? ''
  const openReferenceTab = useRightPanelStore((state) => state.openReferenceTab)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)

  const resolvedViewerContext =
    viewerContext ??
    (referenceKind === 'table'
      ? buildTableViewerContext(resolvedId, activeTaskState)
      : undefined)

  return (
    <span className="standard-reference-link">
      <button
        type="button"
        className="standard-reference-link__button"
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
