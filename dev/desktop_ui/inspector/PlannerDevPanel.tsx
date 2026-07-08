import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import { InspectorAdvancedSection } from './InspectorAdvancedSection'
import { InspectorDebugNotice } from './InspectorDebugNotice'
import { PlannerBlockedReasonSection } from './PlannerBlockedReasonSection'
import { PlannerCurrentStepSection } from './PlannerCurrentStepSection'
import { PlannerPendingWorkSection } from './PlannerPendingWorkSection'
import { PlannerRequiredInputsSection } from './PlannerRequiredInputsSection'
import { PlannerSummarySection } from './PlannerSummarySection'
import { PlannerTraversalTimelineSection } from './PlannerTraversalTimelineSection'

import './InspectorPanels.css'

type PlannerDevPanelProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerDevPanel({ projection }: PlannerDevPanelProps) {
  return (
    <div className="inspector-workflow-status">
      <InspectorDebugNotice />

      <PlannerSummarySection projection={projection} />
      <PlannerCurrentStepSection projection={projection} />
      <PlannerTraversalTimelineSection projection={projection} />
      <PlannerPendingWorkSection projection={projection} />
      <PlannerRequiredInputsSection projection={projection} />
      <PlannerBlockedReasonSection projection={projection} />

      <InspectorAdvancedSection
        title="Advanced Planner JSON"
        data={projection.raw_planner_state}
      />
    </div>
  )
}
