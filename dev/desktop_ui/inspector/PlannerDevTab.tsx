import { useInspectionPayload } from './useInspectionPayload'
import { useInspectorStore } from './inspectorStore'
import { PlannerDevPanel } from './PlannerDevPanel'
import { useDevRenderSpan } from './useDevRenderSpan'

export function PlannerDevTab() {
  const { payload, error, loading } = useInspectionPayload()
  const selectedNodeId = useInspectorStore((state) => state.selectedNodeId)

  useDevRenderSpan('planner_dev_panel_render', Boolean(payload), [payload, selectedNodeId])

  if (loading && !payload) {
    return <p className="inspector-empty">Loading planner state…</p>
  }

  if (!payload) {
    return (
      <p className="inspector-empty">
        {error ? 'Planner inspection requires DEV_INSPECTION_ENABLED=1 on the backend.' : 'No active task.'}
      </p>
    )
  }

  const plannerDecision = selectedNodeId ? payload.planner_decisions[selectedNodeId] ?? null : null

  return <PlannerDevPanel payload={payload} selectedNodeId={selectedNodeId} plannerDecision={plannerDecision} />
}
