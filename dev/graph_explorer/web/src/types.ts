export interface GraphNodeData {
  id: string
  node_type: string
  name: string
  description: string
  pack: string
  metadata: Record<string, unknown>
}

export interface GraphEdgeData {
  id: string
  source: string
  target: string
  edge_type: string
  metadata: Record<string, unknown>
}

export interface GraphContext {
  task_id: string | null
  workflow_id: string | null
  session_id: string
  node_count: number
  edge_count: number
  message?: string | null
}

export interface GraphSnapshot {
  revision: string
  context: GraphContext
  nodes: GraphNodeData[]
  edges: GraphEdgeData[]
}

export interface EdgeRef {
  edge_type: string
  peer_id: string
  direction: string
}

export interface NodeDetail {
  id: string
  node_type: string
  name: string
  description: string
  inputs: string[]
  outputs: string[]
  incoming_edges: EdgeRef[]
  outgoing_edges: EdgeRef[]
  metadata: Record<string, unknown>
  standard_refs: string[]
  body_preview: string
}

export interface GraphAnalysis {
  orphan_nodes: string[]
  no_incoming: string[]
  no_outgoing: string[]
  cycles: string[][]
  duplicate_names: Record<string, string[]>
  disconnected_components: string[][]
  highly_connected: Array<{
    node_id: string
    in_degree: number
    out_degree: number
    total_degree: number
  }>
}

export interface GraphDeltaMessage {
  type: 'delta'
  revision: string
  added_nodes: GraphNodeData[]
  removed_nodes: string[]
  changed_nodes: GraphNodeData[]
  added_edges: GraphEdgeData[]
  removed_edges: string[]
}

export type WebSocketMessage = GraphSnapshot & { type: 'snapshot' } | GraphDeltaMessage

export type ExpansionNodeStatus =
  | 'hidden'
  | 'preview'
  | 'awaiting_expansion_assumption'
  | 'awaiting_decision'
  | 'pending_condition'
  | 'expanded'
  | 'active'
  | 'awaiting_input'
  | 'blocked'
  | 'ready'
  | 'executed'
  | 'skipped'
  | 'failed'
  | 'invalidated'
  | 'unknown'

export type ExpansionEdgeType =
  | 'active'
  | 'inactive'
  | 'conditional'
  | 'skipped'
  | 'blocked'
  | 'reference'
  | 'dependency'

export interface ExpansionNode {
  id: string
  label: string
  type: string
  status: ExpansionNodeStatus
  visible: boolean
  active: boolean
  blocked: boolean
  skipped: boolean
  reason: string
  missing_inputs: string[]
  provided_outputs: string[]
  required_inputs: string[]
  phase: string
  details: Record<string, unknown>
}

export interface ExpansionEdge {
  id: string
  source: string
  target: string
  type: ExpansionEdgeType
  active: boolean
  skipped: boolean
  reason: string
  condition: string
}

export interface ExpansionTimelineItem {
  id: string
  status: string
  value?: unknown
}

export interface ExpansionTimelinePhase {
  phase: string
  status: string
  items: ExpansionTimelineItem[]
}

export interface WorkflowExpansionView {
  revision: string
  task_id: string | null
  workflow: string
  task_status: string
  current_phase: string
  phase_missing: Record<string, string[]>
  inputs: Record<string, { value: unknown; status: string; source: string }>
  expansion_state: Record<string, unknown>
  nodes: ExpansionNode[]
  edges: ExpansionEdge[]
  timeline: ExpansionTimelinePhase[]
  warnings: string[]
  debug: Record<string, unknown>
}

export interface ExpansionViewToggles {
  showSkipped: boolean
  showFullGraph: boolean
  showParameters: boolean
  showReferenceEdges: boolean
  autoRefresh: boolean
}

export const DEFAULT_EXPANSION_TOGGLES: ExpansionViewToggles = {
  showSkipped: true,
  showFullGraph: false,
  showParameters: true,
  showReferenceEdges: false,
  autoRefresh: true,
}
