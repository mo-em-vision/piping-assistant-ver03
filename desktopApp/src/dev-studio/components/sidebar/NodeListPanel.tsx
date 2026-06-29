import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

import type { NodeSummary } from '@/dev-studio/api/devStudioApi'
import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

interface NodeListPanelProps {
  nodes: NodeSummary[]
}

export function NodeListPanel({ nodes }: NodeListPanelProps) {
  const parentRef = useRef<HTMLDivElement>(null)
  const selectedId = useDevStudioStore((s) => s.selectedId)
  const selectedIds = useDevStudioStore((s) => s.selectedIds)
  const loadNode = useDevStudioStore((s) => s.loadNode)
  const toggleSelected = useDevStudioStore((s) => s.toggleSelected)
  const nodeCount = useDevStudioStore((s) => s.nodeCount)

  const virtualizer = useVirtualizer({
    count: nodes.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 12,
  })

  return (
    <>
      <div ref={parentRef} className="dev-studio__list">
        <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
          {virtualizer.getVirtualItems().map((item) => {
            const node = nodes[item.index]
            const active = node.id === selectedId
            const checked = selectedIds.has(node.id)
            return (
              <div
                key={node.id}
                className={`dev-studio__list-item${active ? ' dev-studio__list-item--active' : ''}`}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${item.start}px)`,
                }}
                onClick={() => void loadNode(node.id)}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    e.stopPropagation()
                    toggleSelected(node.id)
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
                <div>
                  <div className="dev-studio__list-item-title">{node.title || node.id}</div>
                  <div className="dev-studio__list-item-meta">
                    {node.type} · {node.id}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        {!nodes.length && <div className="dev-studio__empty">No nodes match your filters.</div>}
      </div>
      <div className="dev-studio__count">{nodeCount} nodes</div>
    </>
  )
}
