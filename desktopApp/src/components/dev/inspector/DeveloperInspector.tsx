import { ExecutionTracePanel } from './ExecutionTracePanel'
import { InspectorGraphPanel } from './InspectorGraphPanel'
import {
  ContextPanel,
  IntegrityTestsPanel,
  LogsPanel,
  PerformancePanel,
  ReplayPanel,
  VariablesPanel,
} from './InspectorPanels'
import { PlannerPanel } from './PlannerPanel'
import { useInspectorStore } from './inspectorStore'
import { useInspectionPayload } from './useInspectionPayload'
import { ValueProvenancePanel } from './ValueProvenancePanel'

import type { InspectorTabId } from '@/types/backend/inspection'

import './DeveloperInspector.css'

const TABS: Array<{ id: InspectorTabId; label: string }> = [
  { id: 'trace', label: 'Execution Trace' },
  { id: 'graph', label: 'Graph' },
  { id: 'planner', label: 'Planner' },
  { id: 'context', label: 'Context' },
  { id: 'variables', label: 'Variables' },
  { id: 'provenance', label: 'Provenance' },
  { id: 'logs', label: 'Logs' },
  { id: 'performance', label: 'Performance' },
  { id: 'integrity', label: 'Integrity' },
  { id: 'replay', label: 'Replay' },
]

export function DeveloperInspector() {
  const open = useInspectorStore((state) => state.open)
  const height = useInspectorStore((state) => state.height)
  const activeTab = useInspectorStore((state) => state.activeTab)
  const setActiveTab = useInspectorStore((state) => state.setActiveTab)
  const selectedNodeId = useInspectorStore((state) => state.selectedNodeId)
  const { payload, error, loading, activeTaskId, sessionId, reload } = useInspectionPayload()

  if (!open) {
    return null
  }

  return (
    <section className="developer-inspector" style={{ height }}>
      <header className="developer-inspector__header">
        <div className="developer-inspector__tabs" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={activeTab === tab.id ? 'developer-inspector__tab--active' : undefined}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="developer-inspector__status">
          {loading ? 'Refreshing…' : null}
          {error ? <span className="developer-inspector__error">{error}</span> : null}
        </div>
      </header>
      <div className="developer-inspector__body">
        {!payload ? (
          <p className="inspector-empty">
            {error ? 'Developer inspection requires DEV_INSPECTION_ENABLED=1 on the backend.' : 'Loading…'}
          </p>
        ) : null}
        {payload && activeTab === 'trace' ? <ExecutionTracePanel steps={payload.execution_trace} /> : null}
        {payload && activeTab === 'graph' ? (
          <InspectorGraphPanel steps={payload.execution_trace} activeTaskId={activeTaskId} />
        ) : null}
        {payload && activeTab === 'planner' ? (
          <PlannerPanel
            decisions={payload.planner_decisions}
            planningSummary={payload.planning_summary}
            selectedNodeId={selectedNodeId}
          />
        ) : null}
        {payload && activeTab === 'context' ? (
          <ContextPanel workflowState={payload.workflow_state} selectedNodeId={selectedNodeId} />
        ) : null}
        {payload && activeTab === 'variables' ? <VariablesPanel workflowState={payload.workflow_state} /> : null}
        {payload && activeTab === 'provenance' ? (
          <ValueProvenancePanel records={payload.provenance_index} warnings={payload.provenance_warnings} />
        ) : null}
        {payload && activeTab === 'logs' ? (
          <LogsPanel executionEvents={payload.execution_events} lifecycleEvents={payload.lifecycle_events} />
        ) : null}
        {payload && activeTab === 'performance' ? <PerformancePanel performance={payload.performance} /> : null}
        {payload && activeTab === 'integrity' ? (
          <IntegrityTestsPanel
            checks={payload.integrity_checks}
            taskId={activeTaskId}
            sessionId={sessionId}
            onRefresh={reload}
          />
        ) : null}
        {payload && activeTab === 'replay' ? (
          <ReplayPanel frames={payload.replay_frames} taskId={activeTaskId} sessionId={sessionId} />
        ) : null}
      </div>
    </section>
  )
}
