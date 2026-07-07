import type { PlannerTraversalInspectorViewDto, PlannerTraversalStateDto } from '@/types/backend/inspection'

import { formatNavigationPhase } from './workflowInspectorLabels'

import './InspectorPanels.css'

type PlannerTraversalPanelProps = {
  traversal?: PlannerTraversalStateDto | null
  view?: PlannerTraversalInspectorViewDto | null
  defaultOpen?: boolean
}

function resolveView(
  traversal: PlannerTraversalStateDto | null | undefined,
  view: PlannerTraversalInspectorViewDto | null | undefined,
): PlannerTraversalInspectorViewDto | null {
  if (view) {
    return view
  }
  if (!traversal) {
    return null
  }
  return {
    current_active_node: traversal.current_active_node ?? null,
    pending_expansion_nodes: traversal.pending_expansion_nodes ?? [],
    expanded_nodes: traversal.expanded_nodes ?? [],
    branch_decisions: traversal.branch_decisions ?? [],
    recent_events: traversal.traversal_events ?? [],
  }
}

export function PlannerTraversalPanel({
  traversal,
  view,
  defaultOpen = true,
}: PlannerTraversalPanelProps) {
  const resolved = resolveView(traversal, view)
  if (!resolved) {
    return <p className="inspector-empty">No planner traversal state.</p>
  }

  return (
    <details className="inspector-rationale-details" open={defaultOpen}>
      <summary>Planner traversal</summary>

      <section className="inspector-workflow-status__section">
        <h4 className="inspector-workflow-status__title">Current active node</h4>
        {resolved.current_active_node ? (
          <dl className="inspector-status-grid">
            <div>
              <dt>Node</dt>
              <dd>
                {resolved.current_active_node.title ?? resolved.current_active_node.node_id}
              </dd>
            </div>
            <div>
              <dt>Id</dt>
              <dd>{resolved.current_active_node.node_id}</dd>
            </div>
            <div>
              <dt>Phase</dt>
              <dd>
                {formatNavigationPhase(resolved.current_active_node.phase ?? '')}
              </dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{resolved.current_active_node.reason}</dd>
            </div>
          </dl>
        ) : (
          <p className="inspector-rationale-meta">No active traversal node.</p>
        )}
      </section>

      {resolved.pending_expansion_nodes.length ? (
        <section className="inspector-workflow-status__section">
          <h4 className="inspector-workflow-status__title">Pending expansion</h4>
          <ul className="inspector-missing-list">
            {resolved.pending_expansion_nodes.map((item) => (
              <li key={item.node_id}>
                <strong>{item.title ?? item.node_id}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.node_type}
                  {item.phase ? `, ${formatNavigationPhase(item.phase)}` : ''})
                </span>
                <p className="inspector-rationale-meta">{item.reason}</p>
                {item.waiting_on.length ? (
                  <p className="inspector-rationale-meta">
                    Waiting on: {item.waiting_on.join(', ')}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {resolved.expanded_nodes.length ? (
        <section className="inspector-workflow-status__section">
          <h4 className="inspector-workflow-status__title">Expanded nodes</h4>
          <ul className="inspector-missing-list">
            {resolved.expanded_nodes.map((item) => (
              <li key={`${item.node_id}-${item.expanded_at_order}`}>
                <strong>{item.title ?? item.node_id}</strong>
                <span className="inspector-rationale-meta"> (order {item.expanded_at_order})</span>
                {item.produced_requirements.length ? (
                  <p className="inspector-rationale-meta">
                    Requirements: {item.produced_requirements.join(', ')}
                  </p>
                ) : null}
                {item.produced_edges.length ? (
                  <p className="inspector-rationale-meta">
                    Edges: {item.produced_edges.join(', ')}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {resolved.branch_decisions.length ? (
        <section className="inspector-workflow-status__section">
          <h4 className="inspector-workflow-status__title">Branch decisions</h4>
          <ul className="inspector-missing-list">
            {resolved.branch_decisions.map((decision) => (
              <li key={decision.field}>
                <strong>{decision.field.replaceAll('_', ' ')}</strong>
                <span className="inspector-rationale-meta"> ({decision.status})</span>
                {decision.candidate_nodes.length ? (
                  <p className="inspector-rationale-meta">
                    Candidates: {decision.candidate_nodes.join(', ')}
                  </p>
                ) : null}
                {decision.selected_node ? (
                  <p className="inspector-rationale-meta">
                    Selected: {decision.selected_node}
                    {decision.value ? ` (${decision.value})` : ''}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {resolved.recent_events.length ? (
        <section className="inspector-workflow-status__section">
          <h4 className="inspector-workflow-status__title">Traversal events</h4>
          <ul className="inspector-missing-list">
            {resolved.recent_events.map((event) => (
              <li key={`${event.order}-${event.event_type}-${event.node_id ?? event.requirement_id ?? ''}`}>
                <span className="inspector-rationale-meta">
                  #{event.order} {event.event_type}
                </span>
                {event.node_id ? (
                  <span className="inspector-rationale-meta"> · {event.node_id}</span>
                ) : null}
                {event.requirement_id ? (
                  <span className="inspector-rationale-meta"> · {event.requirement_id}</span>
                ) : null}
                <p className="inspector-rationale-meta">{event.message}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </details>
  )
}
