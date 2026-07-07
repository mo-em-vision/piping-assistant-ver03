import type {
  EngineeringPlanDto,
  InspectionPayloadDto,
  PlannerInspectorSummaryDto,
  PlannerTraversalInspectorViewDto,
  PlannerTraversalStateDto,
} from '@/types/backend/inspection'

import { isCanonicalEngineeringPlan } from './EngineeringPlanPanel'

const RECENT_EVENT_LIMIT = 20

export function buildPlannerTraversalInspectorView(
  engineeringPlan: EngineeringPlanDto | null | undefined,
): PlannerTraversalInspectorViewDto | null {
  const traversal = engineeringPlan?.traversal
  if (!traversal) {
    return null
  }
  return buildPlannerTraversalInspectorViewFromState(traversal)
}

export function buildPlannerTraversalInspectorViewFromState(
  traversal: PlannerTraversalStateDto,
): PlannerTraversalInspectorViewDto {
  const events = traversal.traversal_events ?? []
  return {
    current_active_node: traversal.current_active_node ?? null,
    pending_expansion_nodes: traversal.pending_expansion_nodes ?? [],
    expanded_nodes: traversal.expanded_nodes ?? [],
    branch_decisions: traversal.branch_decisions ?? [],
    recent_events: events.slice(-RECENT_EVENT_LIMIT),
  }
}

function traversalSummaryFromState(
  traversal: PlannerTraversalStateDto,
): NonNullable<PlannerInspectorSummaryDto['traversal_summary']> {
  return {
    current_active_node_id: traversal.current_active_node_id ?? null,
    current_active_node_title: traversal.current_active_node?.title ?? null,
    pending_expansion_count: traversal.pending_expansion_nodes?.length ?? 0,
    expanded_count: traversal.expanded_nodes?.length ?? 0,
    unresolved_branch_decisions: (traversal.branch_decisions ?? [])
      .filter((item) => item.status === 'unresolved')
      .map((item) => item.field),
  }
}

function resolveCurrentPhase(engineeringPlan: EngineeringPlanDto): string {
  if (engineeringPlan.input_strategy?.current_phase) {
    return engineeringPlan.input_strategy.current_phase
  }
  const activePhase = engineeringPlan.phases?.find((phase) => phase.status === 'active')
  if (activePhase) {
    return activePhase.id
  }
  return engineeringPlan.phases?.[0]?.id ?? ''
}

/**
 * Client-side fallback when only canonical engineering_plan is present.
 * Prefer payload.planner_inspector_summary (rebuilt server-side from the plan).
 */
export function buildPlannerInspectorSummary(
  engineeringPlan: EngineeringPlanDto | null | undefined,
): PlannerInspectorSummaryDto | null {
  if (!engineeringPlan?.root_goal || !engineeringPlan.requirements) {
    return null
  }

  const traversal = engineeringPlan.traversal
  const plannerTraversalView = traversal ? buildPlannerTraversalInspectorViewFromState(traversal) : null

  return {
    root_goal: {
      title: engineeringPlan.root_goal.title,
      target_field: engineeringPlan.root_goal.target_field,
      status: engineeringPlan.root_goal.status,
    },
    current_phase: resolveCurrentPhase(engineeringPlan),
    next_input: null,
    outstanding_required_inputs: [],
    conditional_requirements: [],
    derived_or_lookup_values: [],
    calculations: [],
    planner_graph_summary: {
      selected_subgraph_count: engineeringPlan.graph?.selected_subgraph_node_ids?.length ?? 0,
      expanded_node_count: engineeringPlan.graph?.expanded_node_ids?.length ?? 0,
      dependency_edge_count: engineeringPlan.dependencies?.length ?? 0,
      branch_decision_count: engineeringPlan.graph?.selected_branch_decisions?.length ?? 0,
    },
    traversal_summary: traversal ? traversalSummaryFromState(traversal) : null,
    planner_traversal_view: plannerTraversalView,
    warnings: [],
  }
}

export function resolvePlannerInspectorSummary(
  payload: InspectionPayloadDto,
): PlannerInspectorSummaryDto | null {
  if (payload.planner_inspector_summary && typeof payload.planner_inspector_summary === 'object') {
    return payload.planner_inspector_summary
  }
  if (isCanonicalEngineeringPlan(payload.engineering_plan)) {
    return buildPlannerInspectorSummary(payload.engineering_plan)
  }
  return null
}

export function resolvePlannerTraversalView(
  payload: InspectionPayloadDto,
  summary: PlannerInspectorSummaryDto | null,
): PlannerTraversalInspectorViewDto | null {
  if (summary?.planner_traversal_view) {
    return summary.planner_traversal_view
  }
  if (isCanonicalEngineeringPlan(payload.engineering_plan)) {
    return buildPlannerTraversalInspectorView(payload.engineering_plan)
  }
  return null
}
