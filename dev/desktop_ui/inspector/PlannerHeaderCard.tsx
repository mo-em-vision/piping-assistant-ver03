import type { PlannerInspectorHeaderDto } from '@/types/backend/inspection'

import { InspectorDebugField } from './InspectorDebugNotice'

import './InspectorPanels.css'

const STATUS_LABELS: Record<string, string> = {
  waiting_for_input: 'Waiting for input',
  ready: 'Ready',
  blocked: 'Blocked',
  executing: 'Executing',
  completed: 'Completed',
  invalidated: 'Invalidated',
}

type PlannerHeaderCardProps = {
  header: PlannerInspectorHeaderDto
}

export function PlannerHeaderCard({ header }: PlannerHeaderCardProps) {
  const statusLabel = STATUS_LABELS[header.status_badge] ?? header.status_badge.replaceAll('_', ' ')

  return (
    <section className="inspector-card inspector-card--planner">
      <div className="inspector-card__header">
        <h3 className="inspector-card__title">{header.workflow_name}</h3>
        <span className={`inspector-badge inspector-badge--${header.status_badge}`}>{statusLabel}</span>
      </div>
      <dl className="inspector-status-grid">
        <div>
          <dt>Current step</dt>
          <dd>{header.current_phase_label}</dd>
        </div>
        {header.current_active_node_title || header.current_active_node_id ? (
          <div>
            <dt>Active node</dt>
            <dd>
              {header.current_active_node_title ?? header.current_active_node_id}
              {header.current_active_node_id && header.current_active_node_title ? (
                <span className="inspector-rationale-meta"> ({header.current_active_node_id})</span>
              ) : null}
            </dd>
          </div>
        ) : null}
        {header.next_action ? (
          <div>
            <dt>Waiting for</dt>
            <dd className="inspector-status-highlight">{header.next_action.label}</dd>
          </div>
        ) : null}
        {header.why_here ? <InspectorDebugField label="Why am I here?" value={header.why_here} /> : null}
      </dl>
    </section>
  )
}
