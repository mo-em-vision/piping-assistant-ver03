import { NodeReferenceTab } from '@/components/standards/NodeReferenceTab'
import { TableReferenceTab } from '@/components/standards/TableReferenceTab'
import { useUiStore } from '@/store/uiStore'
import type { StandardsBrowseNodeDto, WorkflowDto } from '@/types/backend/api'

import { collectBrowseIndexEntries } from './standardsBrowseUtils'

interface StandardsBrowserPreviewProps {
  selection: StandardsBrowseNodeDto | null
  onSelect: (node: StandardsBrowseNodeDto) => void
}

function RelatedWorkflows({ workflows }: { workflows: WorkflowDto[] }) {
  const openCreateTaskDialog = useUiStore((state) => state.openCreateTaskDialog)

  if (workflows.length === 0) {
    return null
  }

  return (
    <section className="standards-browser-preview__related" aria-label="Related workflows">
      <h4 className="standards-browser-preview__related-title">Related workflows</h4>
      <ul className="standards-browser-preview__related-list">
        {workflows.map((workflow) => (
          <li key={workflow.id} className="standards-browser-preview__related-item">
            <button
              type="button"
              className="standards-browser-preview__related-button"
              disabled={!workflow.available}
              onClick={() => openCreateTaskDialog(workflow.id)}
            >
              {workflow.name}
            </button>
            <span className="standards-browser-preview__related-meta">
              {workflow.available ? workflow.description : 'Coming soon'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function StandardsBrowserIndexPreview({
  group,
  onSelect,
}: {
  group: StandardsBrowseNodeDto
  onSelect: (node: StandardsBrowseNodeDto) => void
}) {
  const entries = collectBrowseIndexEntries(group)

  if (entries.length === 0) {
    return (
      <p className="standards-browser-preview__placeholder">This section has no indexed entries.</p>
    )
  }

  return (
    <nav className="standards-browser-preview__index" aria-label={`${group.label} index`}>
      <h3 className="standards-browser-preview__index-title">{group.label}</h3>
      <ul className="standards-browser-preview__index-list">
        {entries.map(({ node, depth }) => {
          const isGroup = node.kind === 'group'
          return (
            <li
              key={node.id}
              className="standards-browser-preview__index-item"
              style={{ paddingLeft: `${depth * 0.85}rem` }}
            >
              <button
                type="button"
                className={
                  isGroup
                    ? 'standards-browser-preview__index-heading'
                    : 'standards-browser-preview__index-link'
                }
                onClick={() => onSelect(node)}
              >
                {node.label}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export function StandardsBrowserPreview({ selection, onSelect }: StandardsBrowserPreviewProps) {
  if (!selection) {
    return (
      <p className="standards-browser-preview__placeholder">
        Select a section or node to view the standard index or original text.
      </p>
    )
  }

  if (selection.kind === 'group') {
    return <StandardsBrowserIndexPreview group={selection} onSelect={onSelect} />
  }

  if (selection.kind === 'workflow') {
    const workflow = selection.related_workflows?.[0]
    return (
      <div className="standards-browser-preview__workflow">
        <h3 className="standards-browser-preview__workflow-title">{selection.label}</h3>
        <p className="standards-browser-preview__workflow-description">
          {selection.description ?? workflow?.description ?? 'Engineering workflow entry point.'}
        </p>
        <RelatedWorkflows workflows={selection.related_workflows ?? (workflow ? [workflow] : [])} />
      </div>
    )
  }

  const nodeId = selection.node_id ?? selection.id
  const tableId = selection.table_id ?? nodeId
  const relatedWorkflows = selection.related_workflows ?? []

  return (
    <div className="standards-browser-preview">
      {selection.content_kind === 'table' ? (
        <TableReferenceTab tableId={tableId} />
      ) : (
        <NodeReferenceTab nodeId={nodeId} />
      )}
      <RelatedWorkflows workflows={relatedWorkflows} />
    </div>
  )
}
