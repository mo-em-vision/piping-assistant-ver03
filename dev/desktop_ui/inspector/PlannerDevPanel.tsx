import type {
  InspectionPayloadDto,
  PlannerDecisionDto,
  PlannerInspectorSummaryDto,
} from '@/types/backend/inspection'

import { EngineeringPlanPanel, isEngineeringPlanView } from './EngineeringPlanPanel'
import { asString } from './inspectorUtils'
import { formatNavigationPhase, formatPlannerAction } from './workflowInspectorLabels'

import './InspectorPanels.css'

type PlannerDevPanelProps = {
  payload: InspectionPayloadDto
  selectedNodeId: string | null
  plannerDecision: PlannerDecisionDto | null
}

function plannerSummary(payload: InspectionPayloadDto): PlannerInspectorSummaryDto | null {
  const summary = payload.planner_inspector_summary
  if (summary && typeof summary === 'object') {
    return summary
  }
  const nested = payload.planning_summary?.planner_inspector_summary
  if (nested && typeof nested === 'object') {
    return nested as PlannerInspectorSummaryDto
  }
  return null
}

export function PlannerDevPanel({ payload, selectedNodeId, plannerDecision }: PlannerDevPanelProps) {
  const planningSummary = payload.planning_summary
  const compact = plannerSummary(payload)
  const currentPhase = asString(planningSummary.current_phase)

  return (
    <div className="inspector-workflow-status">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Planner</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Phase</dt>
            <dd>{formatNavigationPhase(currentPhase)}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{formatPlannerAction(asString(planningSummary.action))}</dd>
          </div>
          {compact?.root_goal ? (
            <>
              <div>
                <dt>Root goal</dt>
                <dd>{compact.root_goal.title}</dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd>{compact.root_goal.target_field}</dd>
              </div>
            </>
          ) : planningSummary.goal ? (
            <div>
              <dt>Goal</dt>
              <dd>{String(planningSummary.goal)}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      {compact?.next_input ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Next input</h3>
          <ul className="inspector-missing-list">
            <li>
              <strong>{compact.next_input.label}</strong>
              <span className="inspector-rationale-meta">
                {' '}
                ({compact.next_input.field}, {compact.next_input.phase},{' '}
                {compact.next_input.expected_value_class}, priority {compact.next_input.priority})
              </span>
            </li>
          </ul>
        </section>
      ) : null}

      {compact?.outstanding_required_inputs?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Outstanding required inputs</h3>
          <ul className="inspector-missing-list">
            {compact.outstanding_required_inputs.map((item) => (
              <li key={item.field}>
                <strong>{item.label}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.field}, {item.phase}, {item.expected_value_class}, priority {item.priority}
                  {item.activation_status && item.activation_status !== 'active'
                    ? `, ${item.activation_status}`
                    : ''}
                  )
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {compact?.alternatives?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Alternatives</h3>
          {compact.alternatives.map((group) => (
            <div key={group.resolves}>
              <p className="inspector-rationale-meta">Resolves {group.resolves}</p>
              <ul className="inspector-missing-list">
                {group.options.map((option) => (
                  <li key={option.id}>
                    {option.label} ({option.method})
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ) : null}

      {compact?.derived_or_lookup_values?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Derived / lookup</h3>
          <ul className="inspector-missing-list">
            {compact.derived_or_lookup_values.map((item) => (
              <li key={item.field}>
                {item.field} via {item.method}
                {item.depends_on.length ? ` ← ${item.depends_on.join(', ')}` : ''}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {compact?.planner_graph_summary ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Planner graph</h3>
          <dl className="inspector-status-grid">
            <div>
              <dt>Selected subgraph</dt>
              <dd>{compact.planner_graph_summary.selected_subgraph_count}</dd>
            </div>
            <div>
              <dt>Expanded nodes</dt>
              <dd>{compact.planner_graph_summary.expanded_node_count}</dd>
            </div>
            <div>
              <dt>Dependency edges</dt>
              <dd>{compact.planner_graph_summary.dependency_edge_count}</dd>
            </div>
            <div>
              <dt>Branch decisions</dt>
              <dd>{compact.planner_graph_summary.branch_decision_count}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {compact?.traversal_summary ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Traversal summary</h3>
          <dl className="inspector-status-grid">
            <div>
              <dt>Active node</dt>
              <dd>
                {compact.traversal_summary.current_active_node_title ??
                  compact.traversal_summary.current_active_node_id ??
                  '—'}
              </dd>
            </div>
            <div>
              <dt>Pending expansion</dt>
              <dd>{compact.traversal_summary.pending_expansion_count}</dd>
            </div>
            <div>
              <dt>Expanded</dt>
              <dd>{compact.traversal_summary.expanded_count}</dd>
            </div>
            {compact.traversal_summary.unresolved_branch_decisions.length ? (
              <div>
                <dt>Unresolved branches</dt>
                <dd>{compact.traversal_summary.unresolved_branch_decisions.join(', ')}</dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}

      {compact?.planner_traversal_view ? (
        <details className="inspector-rationale-details" open>
          <summary>Planner traversal</summary>
          <section className="inspector-workflow-status__section">
            <h4 className="inspector-workflow-status__title">Current active node</h4>
            {compact.planner_traversal_view.current_active_node ? (
              <dl className="inspector-status-grid">
                <div>
                  <dt>Node</dt>
                  <dd>
                    {compact.planner_traversal_view.current_active_node.title ??
                      compact.planner_traversal_view.current_active_node.node_id}
                  </dd>
                </div>
                <div>
                  <dt>Phase</dt>
                  <dd>
                    {formatNavigationPhase(
                      compact.planner_traversal_view.current_active_node.phase ?? '',
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{compact.planner_traversal_view.current_active_node.reason}</dd>
                </div>
              </dl>
            ) : (
              <p className="inspector-rationale-meta">No active traversal node.</p>
            )}
          </section>

          {compact.planner_traversal_view.pending_expansion_nodes.length ? (
            <section className="inspector-workflow-status__section">
              <h4 className="inspector-workflow-status__title">Pending expansion</h4>
              <ul className="inspector-missing-list">
                {compact.planner_traversal_view.pending_expansion_nodes.map((item) => (
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

          {compact.planner_traversal_view.expanded_nodes.length ? (
            <section className="inspector-workflow-status__section">
              <h4 className="inspector-workflow-status__title">Expanded nodes</h4>
              <ul className="inspector-missing-list">
                {compact.planner_traversal_view.expanded_nodes.map((item) => (
                  <li key={`${item.node_id}-${item.expanded_at_order}`}>
                    <strong>{item.title ?? item.node_id}</strong>
                    <span className="inspector-rationale-meta">
                      {' '}
                      (order {item.expanded_at_order})
                    </span>
                    {item.produced_requirements.length ? (
                      <p className="inspector-rationale-meta">
                        Requirements: {item.produced_requirements.join(', ')}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {compact.planner_traversal_view.branch_decisions.length ? (
            <section className="inspector-workflow-status__section">
              <h4 className="inspector-workflow-status__title">Branch decisions</h4>
              <ul className="inspector-missing-list">
                {compact.planner_traversal_view.branch_decisions.map((decision) => (
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

          {compact.planner_traversal_view.recent_events.length ? (
            <section className="inspector-workflow-status__section">
              <h4 className="inspector-workflow-status__title">Recent traversal events</h4>
              <ul className="inspector-missing-list">
                {compact.planner_traversal_view.recent_events.map((event) => (
                  <li key={`${event.order}-${event.event_type}`}>
                    <span className="inspector-rationale-meta">
                      #{event.order} {event.event_type}
                    </span>
                    {event.node_id ? (
                      <span className="inspector-rationale-meta"> · {event.node_id}</span>
                    ) : null}
                    <p className="inspector-rationale-meta">{event.message}</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </details>
      ) : null}

      {plannerDecision && selectedNodeId ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Why {selectedNodeId}</h3>
          <p className="inspector-rationale">{plannerDecision.why_selected}</p>
          {plannerDecision.edge_followed ? (
            <p className="inspector-rationale-meta">
              Edge: {plannerDecision.edge_followed.edge_type} ({plannerDecision.edge_followed.from_node} →{' '}
              {plannerDecision.edge_followed.to_node})
            </p>
          ) : null}
        </section>
      ) : null}

      {isEngineeringPlanView(payload.engineering_plan) ? (
        <EngineeringPlanPanel plan={payload.engineering_plan} />
      ) : null}

      {payload.engineering_plan || payload.goals ? (
        <details className="inspector-rationale-details">
          <summary>Debug: raw planner output</summary>
          {payload.engineering_plan && !isEngineeringPlanView(payload.engineering_plan) ? (
            <>
              <h4 className="inspector-workflow-status__title">Engineering plan</h4>
              <pre className="inspector-code">{JSON.stringify(payload.engineering_plan, null, 2)}</pre>
            </>
          ) : null}
          {payload.goals ? (
            <>
              <h4 className="inspector-workflow-status__title">Legacy goals</h4>
              <pre className="inspector-code">{JSON.stringify(payload.goals, null, 2)}</pre>
            </>
          ) : null}
          {isEngineeringPlanView(payload.engineering_plan) ? (
            <>
              <h4 className="inspector-workflow-status__title">Raw engineering plan</h4>
              <p className="inspector-rationale-meta">
                Stored on task outputs as <code>engineering_plan</code> (internal).
              </p>
            </>
          ) : null}
        </details>
      ) : null}
    </div>
  )
}
