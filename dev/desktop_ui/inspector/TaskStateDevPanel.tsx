import { useMemo, useState } from 'react'

import type { InspectionPayloadDto, TaskInspectorSummaryDto } from '@/types/backend/inspection'
import type { CanonicalTaskStateDto, TaskStateDto } from '@/types/backend/api'

import { CanonicalEngineeringPlanPanel, EngineeringPlanPanel, isCanonicalEngineeringPlan, isEngineeringPlanView } from './EngineeringPlanPanel'
import { asString, asStringList } from './inspectorUtils'
import { formatNavigationPhase } from './workflowInspectorLabels'

import './InspectorPanels.css'

type TaskStateDevPanelProps = {
  payload: InspectionPayloadDto
  activeTaskState: TaskStateDto | null
}

type InspectorTab = 'summary' | 'plan' | 'values' | 'graph' | 'progress' | 'lookup' | 'provenance' | 'raw'

const TAB_LABELS: Record<InspectorTab, string> = {
  summary: 'Summary',
  plan: 'Engineering Plan',
  values: 'Values',
  graph: 'Graph',
  progress: 'Progress',
  lookup: 'Lookup Results',
  provenance: 'Provenance',
  raw: 'Raw State',
}

function resolveSummary(
  payload: InspectionPayloadDto,
  activeTaskState: TaskStateDto | null,
): TaskInspectorSummaryDto | null {
  if (payload.inspector_summary) {
    return payload.inspector_summary
  }
  if (activeTaskState?.inspector_summary) {
    return activeTaskState.inspector_summary
  }
  return null
}

function resolveCanonical(
  payload: InspectionPayloadDto,
  activeTaskState: TaskStateDto | null,
): CanonicalTaskStateDto | Record<string, unknown> | null {
  if (payload.canonical_task_state) {
    return payload.canonical_task_state as CanonicalTaskStateDto
  }
  if (activeTaskState?.canonical) {
    return activeTaskState.canonical
  }
  return null
}

export function SummarySection({ summary }: { summary: TaskInspectorSummaryDto }) {
  return (
    <div className="inspector-workflow-status">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Task status</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Status</dt>
            <dd className="inspector-status-highlight">{summary.status ?? '—'}</dd>
          </div>
          <div>
            <dt>Phase</dt>
            <dd>{formatNavigationPhase(summary.phase ?? null)}</dd>
          </div>
          {summary.current_blocker ? (
            <div>
              <dt>Blocker</dt>
              <dd>
                {summary.current_blocker.type}
                {summary.current_blocker.field ? ` · ${summary.current_blocker.field}` : ''}
                {summary.current_blocker.parameter_node_id
                  ? ` (${summary.current_blocker.parameter_node_id})`
                  : ''}
              </dd>
            </div>
          ) : null}
        </dl>
      </section>

      {summary.missing_inputs.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Missing inputs</h3>
          <div className="inspector-node-chips">
            {summary.missing_inputs.map((field) => (
              <span key={field} className="inspector-node-chip inspector-node-chip--pending">
                {field}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {summary.resolved_inputs.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Resolved inputs</h3>
          <dl className="inspector-status-grid">
            {summary.resolved_inputs.map((item) => (
              <div key={item.field}>
                <dt>
                  {item.field}
                  {item.symbol ? ` (${item.symbol})` : ''}
                </dt>
                <dd>
                  {item.display_value}
                  <span className="inspector-status-muted"> · {item.source}</span>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {summary.selected_branch_decisions.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Branch decisions</h3>
          <dl className="inspector-status-grid">
            {summary.selected_branch_decisions.map((decision) => (
              <div key={`${decision.field}-${decision.selected_node}`}>
                <dt>{decision.field}</dt>
                <dd>
                  {decision.value} → {decision.selected_node}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {summary.pending_calculations.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Pending calculations</h3>
          <div className="inspector-node-chips">
            {summary.pending_calculations.map((item) => (
              <span key={item} className="inspector-node-chip">
                {item}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Execution traversal</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Expanded</dt>
            <dd>{summary.execution_graph_summary.expanded_count}</dd>
          </div>
          <div>
            <dt>Active</dt>
            <dd>{summary.execution_graph_summary.active_count}</dd>
          </div>
          <div>
            <dt>Resolved</dt>
            <dd>{summary.execution_graph_summary.resolved_count}</dd>
          </div>
          <div>
            <dt>Pending</dt>
            <dd>{summary.execution_graph_summary.pending_count}</dd>
          </div>
        </dl>
      </section>

      {summary.warnings.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Warnings</h3>
          <ul className="inspector-warning-list">
            {summary.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}

export function TaskStateDevPanel({ payload, activeTaskState }: TaskStateDevPanelProps) {
  const [tab, setTab] = useState<InspectorTab>('summary')
  const summary = useMemo(() => resolveSummary(payload, activeTaskState), [payload, activeTaskState])
  const canonical = useMemo(() => resolveCanonical(payload, activeTaskState), [payload, activeTaskState])
  const engineeringPlan =
    activeTaskState?.engineering_plan ?? payload.engineering_plan
  const engineeringPlanView =
    activeTaskState?.engineering_plan_view ?? payload.engineering_plan_view

  const workflowState = payload.workflow_state
  const currentNode = asString(workflowState.current_node)
  const visitedNodes = asStringList(workflowState.visited_nodes)

  return (
    <div className="inspector-task-state">
      <div className="inspector-task-state__tabs" role="tablist" aria-label="Task state views">
        {(Object.keys(TAB_LABELS) as InspectorTab[]).map((tabId) => (
          <button
            key={tabId}
            type="button"
            role="tab"
            aria-selected={tab === tabId}
            className={`inspector-task-state__tab${tab === tabId ? ' inspector-task-state__tab--active' : ''}`}
            onClick={() => setTab(tabId)}
          >
            {TAB_LABELS[tabId]}
          </button>
        ))}
      </div>

      <div className="inspector-task-state__panel" role="tabpanel">
        {tab === 'summary' ? (
          summary ? (
            <SummarySection summary={summary} />
          ) : (
            <p className="inspector-empty">No inspector summary available.</p>
          )
        ) : null}

        {tab === 'plan' ? (
          isCanonicalEngineeringPlan(engineeringPlan) ? (
            <>
              <CanonicalEngineeringPlanPanel plan={engineeringPlan} />
              {isEngineeringPlanView(engineeringPlanView) ? (
                <EngineeringPlanPanel plan={engineeringPlanView} />
              ) : null}
            </>
          ) : isEngineeringPlanView(engineeringPlanView) ? (
            <EngineeringPlanPanel plan={engineeringPlanView} />
          ) : (
            <p className="inspector-empty">No engineering plan available.</p>
          )
        ) : null}

        {tab === 'values' ? (
          <pre className="inspector-code inspector-code--tall">
            {JSON.stringify((canonical as CanonicalTaskStateDto | null)?.values ?? {}, null, 2)}
          </pre>
        ) : null}

        {tab === 'graph' ? (
          <div className="inspector-workflow-status">
            <section className="inspector-workflow-status__section">
              <h3 className="inspector-workflow-status__title">Graph position</h3>
              <dl className="inspector-status-grid">
                <div>
                  <dt>Current node</dt>
                  <dd className="inspector-status-highlight">{currentNode ?? '—'}</dd>
                </div>
              </dl>
              {visitedNodes.length ? (
                <div className="inspector-node-chips">
                  <span className="inspector-node-chips__label">Visited</span>
                  {visitedNodes.map((nodeId) => (
                    <span
                      key={nodeId}
                      className={`inspector-node-chip${nodeId === currentNode ? ' inspector-node-chip--current' : ''}`}
                    >
                      {nodeId}
                    </span>
                  ))}
                </div>
              ) : null}
            </section>
            <pre className="inspector-code">
              {JSON.stringify((canonical as CanonicalTaskStateDto | null)?.graph ?? {}, null, 2)}
            </pre>
          </div>
        ) : null}

        {tab === 'progress' ? (
          <pre className="inspector-code inspector-code--tall">
            {JSON.stringify(
              (canonical as CanonicalTaskStateDto | null)?.progress ?? activeTaskState?.progress ?? {},
              null,
              2,
            )}
          </pre>
        ) : null}

        {tab === 'lookup' ? (
          <pre className="inspector-code inspector-code--tall">
            {JSON.stringify((canonical as CanonicalTaskStateDto | null)?.lookup_results ?? {}, null, 2)}
          </pre>
        ) : null}

        {tab === 'provenance' ? (
          <pre className="inspector-code inspector-code--tall">
            {JSON.stringify(payload.provenance_index ?? [], null, 2)}
          </pre>
        ) : null}

        {tab === 'raw' ? (
          <div className="inspector-workflow-status">
            {activeTaskState ? (
              <section className="inspector-workflow-status__section">
                <h3 className="inspector-workflow-status__title">Backend task state</h3>
                <pre className="inspector-code inspector-code--tall">
                  {JSON.stringify(activeTaskState, null, 2)}
                </pre>
              </section>
            ) : null}
            <section className="inspector-workflow-status__section">
              <h3 className="inspector-workflow-status__title">Inspection payload</h3>
              <pre className="inspector-code inspector-code--tall">{JSON.stringify(payload, null, 2)}</pre>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  )
}
