import { ExecutionTracePanel } from './ExecutionTracePanel'
import { InspectorGraphPanel } from './InspectorGraphPanel'
import { InspectorResizeHandle } from './InspectorResizeHandle'
import { PerformanceTracePanel } from './PerformanceTracePanel'
import { useInspectorStore } from './inspectorStore'
import { useInspectionPayload } from './useInspectionPayload'
import { useDevRenderSpan } from './useDevRenderSpan'
import { formatNavigationPhase } from './workflowInspectorLabels'

import './DeveloperInspector.css'

export function DeveloperInspector() {
  const open = useInspectorStore((state) => state.open)
  const height = useInspectorStore((state) => state.height)
  const selectedNodeId = useInspectorStore((state) => state.selectedNodeId)
  const { payload, error, loading, activeTaskId, sessionId } = useInspectionPayload()

  useDevRenderSpan('inspector_panel_render', open, [payload, loading, error])

  if (!open) {
    return null
  }

  const currentPhase = payload ? String(payload.planning_summary.current_phase ?? '') : ''
  const currentNode = payload ? String(payload.workflow_state.current_node ?? '') : ''

  return (
    <section className="developer-inspector" style={{ height }}>
      <InspectorResizeHandle />
      <header className="developer-inspector__header">
        <div className="developer-inspector__title">
          <strong>Workflow Inspector</strong>
          {payload ? (
            <span className="developer-inspector__summary">
              {formatNavigationPhase(currentPhase)}
              {currentNode ? ` · ${currentNode}` : ''}
            </span>
          ) : null}
        </div>
        <div className="developer-inspector__status">
          {loading ? 'Refreshing…' : null}
          {error ? <span className="developer-inspector__error">{error}</span> : null}
        </div>
      </header>
      <div className="developer-inspector__body">
        <div className="developer-inspector__layout">
          <aside className="developer-inspector__sidebar">
            <PerformanceTracePanel />
            {payload ? (
              <section className="inspector-trace-section">
                <h3 className="inspector-workflow-status__title">Execution steps</h3>
                <ExecutionTracePanel steps={payload.execution_trace} />
              </section>
            ) : null}
          </aside>
          <main className="developer-inspector__graph">
            {!payload ? (
              <p className="inspector-empty">
                {error
                  ? 'Developer inspection requires DEV_INSPECTION_ENABLED=1 on the backend.'
                  : 'Loading workflow inspection…'}
              </p>
            ) : (
              <InspectorGraphPanel
                activeTaskId={activeTaskId}
                sessionId={sessionId}
                focusNodeId={selectedNodeId}
              />
            )}
          </main>
        </div>
      </div>
    </section>
  )
}
