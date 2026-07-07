import type { InspectionPayloadDto, PlannerDecisionDto } from '@/types/backend/inspection'

import { CanonicalEngineeringPlanPanel, EngineeringPlanPanel, isCanonicalEngineeringPlan, isEngineeringPlanView } from './EngineeringPlanPanel'
import { PlannerTraversalPanel } from './PlannerTraversalPanel'
import {
  resolvePlannerInspectorSummary,
  resolvePlannerTraversalView,
} from './plannerInspectorSummary'
import { validateEngineeringPlan } from './validateEngineeringPlan'
import { asString } from './inspectorUtils'
import { formatNavigationPhase } from './workflowInspectorLabels'

import './InspectorPanels.css'

type PlannerDevPanelProps = {
  payload: InspectionPayloadDto
  selectedNodeId: string | null
  plannerDecision: PlannerDecisionDto | null
}

function formatRootGoalStatus(status: string): string {
  switch (status) {
    case 'blocked':
      return 'Blocked on inputs'
    case 'ready':
      return 'Ready to execute'
    case 'complete':
      return 'Complete'
    case 'active':
      return 'In progress'
    default:
      return status.replace(/_/g, ' ')
  }
}

export function PlannerDevPanel({ payload, selectedNodeId, plannerDecision }: PlannerDevPanelProps) {
  const compact = resolvePlannerInspectorSummary(payload)
  const traversalView = resolvePlannerTraversalView(payload, compact)
  const currentPhase = compact?.current_phase ?? null
  const planValidation = isCanonicalEngineeringPlan(payload.engineering_plan)
    ? validateEngineeringPlan(payload.engineering_plan)
    : null
  const planDebugWarnings = payload.engineering_plan?.debug?.warnings ?? []
  const validationMessages = [
    ...(compact?.warnings ?? []),
    ...planDebugWarnings,
    ...(planValidation?.warnings ?? []),
    ...(planValidation?.errors ?? []),
  ]

  return (
    <div className="inspector-workflow-status">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Planner</h3>
        <p className="inspector-rationale-meta">
          Source: <code>engineering_plan</code>
        </p>
        <dl className="inspector-status-grid">
          <div>
            <dt>Phase</dt>
            <dd>{formatNavigationPhase(currentPhase)}</dd>
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
              <div>
                <dt>Goal status</dt>
                <dd>{formatRootGoalStatus(compact.root_goal.status)}</dd>
              </div>
            </>
          ) : (
            <div>
              <dt>Plan</dt>
              <dd className="inspector-rationale-meta">No engineering plan on task.</dd>
            </div>
          )}
        </dl>
      </section>

      {planValidation ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Plan validation</h3>
          <p className="inspector-rationale-meta">
            {planValidation.valid ? 'Valid normalized engineering plan.' : 'Validation failed.'}
          </p>
          {validationMessages.length ? (
            <ul className="inspector-missing-list inspector-warnings">
              {validationMessages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

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

      {compact?.conditional_requirements?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Conditional future requirements</h3>
          <ul className="inspector-missing-list">
            {compact.conditional_requirements.map((item) => (
              <li key={item.field}>
                <strong>{item.title}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.field}, {item.phase})
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
          <h3 className="inspector-workflow-status__title">Derived / lookup requirements</h3>
          <ul className="inspector-missing-list">
            {compact.derived_or_lookup_values.map((item) => (
              <li key={item.field}>
                <strong>{item.title ?? item.field}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  via {item.method}
                  {item.source_node_id ? ` (${item.source_node_id})` : ''}
                  {item.depends_on.length ? ` ← ${item.depends_on.join(', ')}` : ''}
                  {item.activation_status && item.activation_status !== 'active'
                    ? `, ${item.activation_status}`
                    : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {compact?.calculations?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Calculations</h3>
          <ul className="inspector-missing-list">
            {compact.calculations.map((item) => (
              <li key={item.field}>
                <strong>{item.title}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.field}, {item.status}
                  {item.depends_on.length ? ` ← ${item.depends_on.join(', ')}` : ''})
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {compact?.system_resolved_requirements?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">System-resolved requirements</h3>
          <ul className="inspector-missing-list">
            {compact.system_resolved_requirements.map((item) => (
              <li key={item.id}>
                <strong>{item.title}</strong>
                <span className="inspector-rationale-meta">
                  {' '}
                  ({item.requirement_class.replace('_', ' ')}, {item.method}
                  {item.source_node_id ? `, ${item.source_node_id}` : ''}
                  {item.depends_on.length ? ` ← ${item.depends_on.join(', ')}` : ''}
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

      {compact?.planner_graph_summary ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Dependency graph summary</h3>
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

      {traversalView || payload.engineering_plan?.traversal ? (
        <PlannerTraversalPanel
          traversal={payload.engineering_plan?.traversal}
          view={traversalView ?? undefined}
        />
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

      {isCanonicalEngineeringPlan(payload.engineering_plan) ? (
        <details className="inspector-rationale-details">
          <summary>Canonical engineering plan (debug)</summary>
          <CanonicalEngineeringPlanPanel plan={payload.engineering_plan} />
        </details>
      ) : null}

      {isEngineeringPlanView(payload.engineering_plan_view) ? (
        <details className="inspector-rationale-details">
          <summary>Engineering plan view (debug)</summary>
          <EngineeringPlanPanel plan={payload.engineering_plan_view} />
        </details>
      ) : null}

      {payload.legacy_goal_map || payload.goals ? (
        <details className="inspector-rationale-details">
          <summary>Legacy goal map (deprecated)</summary>
          <p className="inspector-rationale-meta">
            Backward-compatible projection from <code>goal_store</code>. Prefer{' '}
            <code>engineering_plan</code> as the source of truth.
          </p>
          <pre className="inspector-code">
            {JSON.stringify(payload.legacy_goal_map ?? payload.goals, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  )
}
