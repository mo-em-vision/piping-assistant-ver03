import type { InspectionPayloadDto, PlannerDecisionDto } from '@/types/backend/inspection'

import { InspectorAdvancedSection } from './InspectorAdvancedSection'
import { InspectorDebugNotice } from './InspectorDebugNotice'
import { InspectorDisclosureSection } from './InspectorDisclosureSection'
import { isCanonicalEngineeringPlan, isEngineeringPlanView } from './EngineeringPlanPanel'
import { PlannerHeaderCard } from './PlannerHeaderCard'
import { PlannerPhasePanel } from './PlannerPhasePanel'
import { PlannerRequirementsPanel } from './PlannerRequirementsPanel'
import { PlannerTraversalTimeline } from './PlannerTraversalTimeline'
import { PlannerWarningsPanel } from './PlannerWarningsPanel'
import { resolvePlannerInspectorSummary } from './plannerInspectorSummary'
import { validateEngineeringPlan } from './validateEngineeringPlan'

import './InspectorPanels.css'

type PlannerDevPanelProps = {
  payload: InspectionPayloadDto
  selectedNodeId: string | null
  plannerDecision: PlannerDecisionDto | null
}

export function PlannerDevPanel({ payload, selectedNodeId, plannerDecision }: PlannerDevPanelProps) {
  const compact = resolvePlannerInspectorSummary(payload)
  const planValidation = isCanonicalEngineeringPlan(payload.engineering_plan)
    ? validateEngineeringPlan(payload.engineering_plan)
    : null

  if (!compact) {
    return <p className="inspector-empty">No engineering plan on task.</p>
  }

  const requirementCount = compact.requirements_panel?.length ?? 0
  const phaseSummary = compact.phase_panel
    ? `${compact.phase_panel.completed_fields.length} completed · ${compact.phase_panel.missing_in_phase.length} missing · ${compact.phase_panel.future_fields.length} future`
    : undefined

  return (
    <div className="inspector-workflow-status">
      <InspectorDebugNotice />

      {compact.header ? <PlannerHeaderCard header={compact.header} /> : null}

      <PlannerTraversalTimeline
        rows={compact.traversal_path ?? []}
        supportLevel={compact.header?.traversal_support_level}
        supportNote={compact.header?.traversal_support_note}
      />

      {compact.phase_panel ? (
        <InspectorDisclosureSection title="Planner phase details" summary={phaseSummary} defaultOpen>
          <PlannerPhasePanel panel={compact.phase_panel} />
        </InspectorDisclosureSection>
      ) : null}

      {requirementCount ? (
        <InspectorDisclosureSection
          title="Requirements"
          summary={`${requirementCount} tracked`}
        >
          <PlannerRequirementsPanel rows={compact.requirements_panel ?? []} />
        </InspectorDisclosureSection>
      ) : null}

      <PlannerWarningsPanel
        warnings={compact.warnings}
        planValid={planValidation?.valid ?? null}
        planValidationMessages={[
          ...(planValidation?.warnings ?? []),
          ...(planValidation?.errors ?? []),
        ]}
      />

      {selectedNodeId && plannerDecision ? (
        <InspectorDisclosureSection
          title={`Trace step: ${selectedNodeId}`}
          summary="Inspector execution trace rationale"
        >
          <p>{plannerDecision.why_selected}</p>
          {plannerDecision.rejected_candidates.length ? (
            <ul className="inspector-missing-list">
              {plannerDecision.rejected_candidates.map((candidate) => (
                <li key={candidate.node_id}>
                  {candidate.node_id}: {candidate.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </InspectorDisclosureSection>
      ) : null}

      <InspectorAdvancedSection title="Advanced / Raw Data — Canonical engineering plan" data={payload.engineering_plan} />
      {isEngineeringPlanView(payload.engineering_plan_view) ? (
        <InspectorAdvancedSection title="Engineering plan view (raw)" data={payload.engineering_plan_view} />
      ) : null}
      {payload.legacy_goal_map ? (
        <InspectorAdvancedSection
          title="Legacy goal map — do not use as planner source of truth"
          data={payload.legacy_goal_map}
          deprecated
        />
      ) : null}
      {compact.planner_traversal_view ? (
        <InspectorAdvancedSection
          title="Planner traversal view (raw)"
          data={compact.planner_traversal_view}
        />
      ) : null}
    </div>
  )
}
