import {
  useRightPanelStore,
  type NodeViewerContext,
  type StandardsReferenceKind,
  type TableViewerContext,
} from '@/store/rightPanelStore'
import { DevNodeHoverSurface } from '@dev-ui/DevNodeHoverSurface'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import type { NodeProvenanceDto } from '@/types/backend/api'
import { buildTableViewerContext } from '@/utils/tableViewerContext'

import './StandardReferenceLink.css'

interface StandardReferenceLinkProps {
  referenceKind?: StandardsReferenceKind
  referenceId?: string
  subsectionId?: string
  nodeId?: string
  label: string
  viewerContext?: TableViewerContext | NodeViewerContext
  provenance?: NodeProvenanceDto | null
  /** When false, open the reference tab without leaving the current panel view. */
  activateTab?: boolean
}

export function StandardReferenceLink({
  referenceKind = 'node',
  referenceId,
  subsectionId,
  nodeId,
  label,
  viewerContext,
  provenance,
  activateTab = true,
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

  return (
    <span className="standard-reference-link">
      <DevNodeHoverSurface provenance={provenance}>
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
      </DevNodeHoverSurface>
    </span>
  )
}
