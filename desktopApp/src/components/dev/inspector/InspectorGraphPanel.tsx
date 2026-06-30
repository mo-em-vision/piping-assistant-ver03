import type { ExecutionTraceStepDto } from '@/types/backend/inspection'

import { useInspectorStore } from './inspectorStore'

import './InspectorPanels.css'

const STATE_CLASS: Record<string, string> = {
  pending: 'inspector-graph-node--pending',
  success: 'inspector-graph-node--success',
  failed: 'inspector-graph-node--failed',
  skipped: 'inspector-graph-node--skipped',
  awaiting_input: 'inspector-graph-node--active',
}

type InspectorGraphPanelProps = {
  steps: ExecutionTraceStepDto[]
  activeTaskId: string | null
}

export function InspectorGraphPanel({ steps, activeTaskId }: InspectorGraphPanelProps) {
  const selectedNodeId = useInspectorStore((state) => state.selectedNodeId)
  const selectNode = useInspectorStore((state) => state.selectNode)

  const openExplorer = () => {
    if (!activeTaskId) {
      return
    }
    window.open(`http://localhost:3000?task=${encodeURIComponent(activeTaskId)}`, '_blank')
  }

  return (
    <div className="inspector-graph">
      <div className="inspector-graph__toolbar">
        <button type="button" onClick={openExplorer}>
          Open in Graph Explorer
        </button>
      </div>
      <div className="inspector-graph__canvas">
        {steps.map((step) => {
          const selected = selectedNodeId === step.node_id
          const stateClass = STATE_CLASS[step.status] ?? 'inspector-graph-node--pending'
          return (
            <button
              key={`${step.step_index}-${step.node_id}`}
              type="button"
              className={`inspector-graph-node ${stateClass}${selected ? ' inspector-graph-node--selected' : ''}`}
              onClick={() => selectNode(step.node_id)}
              title={step.selection_reason}
            >
              <span className="inspector-graph-node__id">{step.node_id}</span>
              <span className="inspector-graph-node__status">{step.status}</span>
            </button>
          )
        })}
      </div>
      {selectedNodeId ? (
        <div className="inspector-graph__detail">
          <strong>{selectedNodeId}</strong>
        </div>
      ) : null}
    </div>
  )
}
