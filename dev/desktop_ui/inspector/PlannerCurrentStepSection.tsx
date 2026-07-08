import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import { displayValue } from './plannerDebugDisplay'

import './InspectorPanels.css'

type PlannerCurrentStepSectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerCurrentStepSection({ projection }: PlannerCurrentStepSectionProps) {
  const active = projection.active_node

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Current Execution Step</h3>
      <dl className="inspector-status-grid">
        <div>
          <dt>Active node id</dt>
          <dd>{displayValue(active?.node_id)}</dd>
        </div>
        <div>
          <dt>Active node label</dt>
          <dd>{displayValue(active?.title)}</dd>
        </div>
        <div>
          <dt>Node type</dt>
          <dd>{displayValue(active?.node_type)}</dd>
        </div>
        <div>
          <dt>Why active</dt>
          <dd>{displayValue(active?.why_active)}</dd>
        </div>
        <div>
          <dt>Next expected action</dt>
          <dd className="inspector-status-highlight">
            {displayValue(projection.next_expected_action)}
          </dd>
        </div>
      </dl>
    </section>
  )
}
