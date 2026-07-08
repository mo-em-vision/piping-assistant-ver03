import { useInspectionPayload } from './useInspectionPayload'
import { PlannerDevPanel } from './PlannerDevPanel'
import { useDevRenderSpan } from './useDevRenderSpan'

export function PlannerDevTab() {
  const { payload, error, loading } = useInspectionPayload()

  useDevRenderSpan('planner_dev_panel_render', Boolean(payload?.planner_debug_projection), [
    payload?.planner_debug_projection,
  ])

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

  const projection = payload.planner_debug_projection
  if (!projection) {
    return <p className="inspector-empty">Planner debug projection not available.</p>
  }

  return <PlannerDevPanel projection={projection} />
}
