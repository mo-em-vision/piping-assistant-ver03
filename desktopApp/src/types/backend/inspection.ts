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

export type InspectionPayloadDto = {
  task_id: string
  workflow_id: string
  execution_trace: ExecutionTraceStepDto[]
  planner_decisions: Record<string, PlannerDecisionDto>
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
}

export type InspectorTabId =
  | 'trace'
  | 'graph'
  | 'planner'
  | 'context'
  | 'variables'
  | 'provenance'
  | 'logs'
  | 'performance'
  | 'integrity'
  | 'replay'
