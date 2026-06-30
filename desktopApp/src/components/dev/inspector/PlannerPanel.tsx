import type { PlannerDecisionDto } from '@/types/backend/inspection'

import { useInspectorStore } from './inspectorStore'

import './InspectorPanels.css'

type PlannerPanelProps = {
  decisions: Record<string, PlannerDecisionDto>
  planningSummary: Record<string, unknown>
  selectedNodeId: string | null
}

export function PlannerPanel({ decisions, planningSummary, selectedNodeId }: PlannerPanelProps) {
  const decision = selectedNodeId ? decisions[selectedNodeId] : null

  return (
    <div className="inspector-planner">
      <section>
        <h4>Planning summary</h4>
        <pre className="inspector-code">{JSON.stringify(planningSummary, null, 2)}</pre>
      </section>
      {decision ? (
        <section>
          <h4>Selected: {decision.node_id}</h4>
          <p>
            <strong>Why:</strong> {decision.why_selected}
          </p>
          {decision.trigger_dependency ? (
            <p>
              <strong>Requires:</strong> {decision.trigger_dependency}
            </p>
          ) : null}
          {decision.edge_followed ? (
            <p>
              <strong>Edge:</strong> {decision.edge_followed.edge_type} ({decision.edge_followed.from_node} →{' '}
              {decision.edge_followed.to_node})
            </p>
          ) : null}
          <p>
            <strong>Rule:</strong> {decision.rule_fired}
          </p>
          {decision.rejected_candidates.length ? (
            <div>
              <strong>Rejected:</strong>
              <ul>
                {decision.rejected_candidates.map((item) => (
                  <li key={item.node_id}>
                    {item.node_id} ({item.reason})
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : (
        <p className="inspector-empty">Select a trace step to inspect planner rationale.</p>
      )}
    </div>
  )
}
