import './InspectorPanels.css'

import { useDevRenderSpan } from './useDevRenderSpan'

type InspectorGraphPanelProps = {
  activeTaskId: string | null
  sessionId: string | null
  focusNodeId?: string | null
}

export function InspectorGraphPanel({ activeTaskId }: InspectorGraphPanelProps) {
  useDevRenderSpan('graph_visualizer_render', Boolean(activeTaskId), [activeTaskId])
  if (!activeTaskId) {
    return (
      <div className="inspector-graph">
        <p className="inspector-graph__hint">Open a task to inspect workflow state.</p>
      </div>
    )
  }

  return (
    <div className="inspector-graph">
      <p className="inspector-graph__hint">
        Graph visualization has been removed. Use the execution steps panel for workflow trace details.
      </p>
    </div>
  )
}
