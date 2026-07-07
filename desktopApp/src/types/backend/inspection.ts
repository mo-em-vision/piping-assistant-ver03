export type GraphEdgeRefDto = {
  from_node: string
  to_node: string
  edge_type: string
}

export type ExecutionTraceStepDto = {
  step_index: number
  workflow_id: string
  node_id: string
  node_type: string
  incoming_edge: GraphEdgeRefDto | null
  outgoing_edge: GraphEdgeRefDto | null
  selection_reason: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  duration_ms: number | null
  status: string
  timestamp?: string | null
  errors?: string[]
  warnings?: string[]
}

export type PlannerDecisionDto = {
  node_id: string
  why_selected: string
  trigger_dependency: string | null
  edge_followed: GraphEdgeRefDto | null
  rule_fired: string
  rejected_candidates: Array<{ node_id: string; reason: string }>
}

export type ValueProvenanceRecordDto = {
  display_id: string
  display_value: string
  source_node: string
  source_property: string
  generated_by?: string | null
  consumed_by?: string[]
  transformation_history?: Array<Record<string, unknown>>
  missing?: boolean
}

export type ReplayFrameDto = {
  frame_index: number
  step_index: number | null
  active_node: string | null
  visited_nodes: string[]
  pending_nodes: string[]
  variables: Record<string, unknown>
  outputs: Record<string, unknown>
  planner_state: Record<string, unknown>
  context: Record<string, unknown>
}

export type IntegrityCheckDto = {
  check_id: string
  name: string
  passed: boolean
  message: string
  details?: Record<string, unknown>
}

export type PlannerInspectorSummaryDto = {
  root_goal: {
    title: string
    target_field: string
    status: string
  }
  current_phase: string
  next_input?: {
    field: string
    label: string
    phase: string
    expected_value_class: string
    allowed_units?: string[]
    priority: number
    activation_status?: 'active' | 'conditional' | 'not_applicable'
  } | null
  outstanding_required_inputs: Array<{
    field: string
    label: string
    phase: string
    expected_value_class: string
    allowed_units?: string[]
    priority: number
    activation_status?: 'active' | 'conditional' | 'not_applicable'
  }>
  conditional_requirements: Array<{
    field: string
    title: string
    phase: string
    activation_condition: unknown
  }>
  alternatives?: Array<{
    resolves: string
    options: Array<{
      id: string
      label: string
      fields: string[]
      method: string
    }>
  }>
  derived_or_lookup_values: Array<{
    id?: string
    field: string
    title?: string
    method: string
    depends_on: string[]
    status: string
    source_node_id?: string
    activation_status?: string
  }>
  calculations: Array<{
    field: string
    title: string
    depends_on: string[]
    status: string
  }>
  system_resolved_requirements?: Array<{
    id: string
    field: string
    title: string
    requirement_class: string
    method: string
    depends_on: string[]
    status: string
    phase: string
    source_node_id?: string
    activation_status?: string
  }>
  planner_graph_summary: {
    selected_subgraph_count: number
    expanded_node_count: number
    dependency_edge_count: number
    branch_decision_count: number
  }
  traversal_summary?: {
    current_active_node_id: string | null
    current_active_node_title?: string | null
    pending_expansion_count: number
    expanded_count: number
    unresolved_branch_decisions: string[]
  } | null
  planner_traversal_view?: PlannerTraversalInspectorViewDto | null
  warnings: string[]
}

export type PlannerTraversalStateDto = {
  traversal_id: string
  current_active_node_id: string | null
  current_active_node: {
    node_id: string
    node_type: string
    title?: string
    phase?: string
    reason: string
  } | null
  pending_expansion_nodes: Array<{
    node_id: string
    node_type: string
    title?: string
    phase?: string
    waiting_on: string[]
    reason: string
  }>
  expanded_nodes: Array<{
    node_id: string
    node_type: string
    title?: string
    expanded_at_order: number
    produced_requirements: string[]
    produced_edges: string[]
  }>
  branch_decisions: Array<{
    field: string
    value: string | null
    selected_node: string | null
    candidate_nodes: string[]
    status: 'unresolved' | 'resolved'
  }>
  traversal_events: Array<{
    order: number
    event_type:
      | 'node_selected'
      | 'node_expanded'
      | 'requirement_created'
      | 'edge_created'
      | 'branch_decision_required'
      | 'branch_decision_resolved'
      | 'node_deferred'
      | 'node_marked_not_applicable'
    node_id?: string
    requirement_id?: string
    edge_id?: string
    message: string
  }>
}

export type PlannerTraversalInspectorViewDto = {
  current_active_node: {
    node_id: string
    node_type: string
    title?: string
    phase?: string
    reason: string
  } | null
  pending_expansion_nodes: Array<{
    node_id: string
    node_type: string
    title?: string
    phase?: string
    waiting_on: string[]
    reason: string
  }>
  expanded_nodes: Array<{
    node_id: string
    node_type: string
    title?: string
    expanded_at_order: number
    produced_requirements: string[]
    produced_edges: string[]
  }>
  branch_decisions: Array<{
    field: string
    value: string | null
    selected_node: string | null
    candidate_nodes: string[]
    status: 'unresolved' | 'resolved'
  }>
  recent_events: Array<{
    order: number
    event_type:
      | 'node_selected'
      | 'node_expanded'
      | 'requirement_created'
      | 'edge_created'
      | 'branch_decision_required'
      | 'branch_decision_resolved'
      | 'node_deferred'
      | 'node_marked_not_applicable'
    node_id?: string
    requirement_id?: string
    edge_id?: string
    message: string
  }>
}

export type EngineeringPlanDto = {
  plan_id: string
  task_id: string
  workflow_id: string
  root_goal: {
    id: string
    key: string
    title: string
    goal_class: 'calculation_goal'
    target_parameter: string
    target_field: string
    status: string
    blocked_by: string[]
    provisional_blocked_by?: string[]
    required_outputs: string[]
  }
  requirements: Record<
    string,
    {
      id: string
      key: string
      field: string
      title: string
      parameter_node_id: string | null
      requirement_class: string
      status: string
      phase: string
      required_by: string[]
      depends_on: string[]
      activation_status?: string
    }
  >
  dependencies: Array<{
    from: string
    to: string
    type: string
  }>
  input_strategy?: {
    mode: string
    current_phase: string
    next_fields: string[]
    blocked_fields: string[]
    resolved_fields: string[]
  }
  phases: Array<{
    id: string
    title: string
    order: number
    requirement_ids: string[]
    status: string
  }>
  graph: {
    selected_subgraph_node_ids: string[]
    selected_branch_decisions: Array<{
      field: string
      value: string
      selected_node: string
    }>
    expanded_node_ids: string[]
  }
  traversal?: PlannerTraversalStateDto
  legacy_goal_map?: Record<string, unknown>
  debug?: {
    warnings: string[]
    source?: string
  }
}

export type EngineeringPlanViewDto = {
  overview: {
    goal: string
    target: string
    goal_status: string
    goal_status_label: string
    workflow_id: string
    current_phase?: string | null
    resolved_count: number
    remaining_count: number
    next_input?: { field: string; label: string } | null
  }
  phases: Array<{
    id: string
    title: string
    status: string
    status_label: string
    requirements: Array<{
      field: string
      label: string
      kind: string
      status: string
      status_label: string
      depends_on?: string[]
      alternatives?: Array<{ label: string; method: string; fields: string[] }>
    }>
  }>
  calculations: Array<{
    field: string
    label: string
    kind: string
    status: string
    status_label: string
  }>
  branch_decisions?: Array<{ field: string; value: string; selected_node: string }>
  input_strategy?: {
    mode: string
    resolved_fields: string[]
    blocked_fields: string[]
    next_fields: string[]
  }
  warnings?: string[]
}

export type InspectionPayloadDto = {
  task_id: string
  workflow_id: string
  execution_trace: ExecutionTraceStepDto[]
  planner_decisions: Record<string, PlannerDecisionDto>
  /** @deprecated Use legacy_goal_map */
  goals?: Record<string, unknown>
  legacy_goal_map?: Record<string, unknown>
  /** Normalized canonical engineering plan (source of truth). */
  engineering_plan?: EngineeringPlanDto | null
  /** Human-readable plan summary for inspector UI. */
  engineering_plan_view?: EngineeringPlanViewDto | null
  planner_inspector_summary?: PlannerInspectorSummaryDto
  execution_context?: Record<string, unknown>
  authority_context?: Record<string, unknown>
  planning_summary: Record<string, unknown>
  provenance_index: ValueProvenanceRecordDto[]
  provenance_warnings: string[]
  workflow_state: Record<string, unknown>
  execution_events: Array<Record<string, unknown>>
  lifecycle_events: Array<Record<string, unknown>>
  replay_frames: ReplayFrameDto[]
  replay_snapshot: Record<string, unknown>
  integrity_checks: IntegrityCheckDto[]
  performance: {
    total_duration_ms: number
    step_count: number
    by_node_ms: Record<string, number>
  }
  breakpoint: { paused?: boolean; step_once?: boolean }
  inspector_summary?: TaskInspectorSummaryDto
  canonical_task_state?: Record<string, unknown>
}

export type DevOperationDto = {
  id: string
  name: string
  category: string
  status: string
  elapsed_ms?: number
  duration_ms?: number | null
  started_at: number
  started_at_epoch_ms?: number
  finished_at?: number | null
  parent_id?: string | null
  error?: string | null
  metadata?: Record<string, unknown>
}

export type DevOperationsSnapshotDto = {
  running: DevOperationDto[]
  recent: DevOperationDto[]
}

export type TaskInspectorSummaryDto = {
  status?: string
  phase?: string
  current_blocker?: {
    type: string
    field?: string
    parameter_node_id?: string
    message?: string
  }
  resolved_inputs: Array<{
    field: string
    symbol?: string
    display_value: string
    source: string
  }>
  missing_inputs: string[]
  selected_branch_decisions: Array<{
    field: string
    value: string
    selected_node: string
  }>
  pending_calculations: string[]
  execution_graph_summary: {
    expanded_count: number
    active_count: number
    resolved_count: number
    pending_count: number
  }
  warnings: string[]
}

