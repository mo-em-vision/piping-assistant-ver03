import type { DisplayOutputBlock } from '@/types/backend/outputs'
import type {
  EngineeringPlanDto,
  EngineeringPlanViewDto,
  PerformanceTraceDto,
} from '@/types/backend/inspection'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { TaskStatus } from '@/types/frontend/workspace'

export type TaskSummaryDto = {
  id: string
  name: string
  description: string
  discipline: string
  workflow_id: string
  status: string
  project_id?: string
  project_name?: string
}

export interface ApiRecoveryInfo {
  title: string
  what_happened: string
  possible_reason: string
  next_action: string
  affected_parameter?: string
  affected_task?: string
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown>
  recovery?: ApiRecoveryInfo
}

export interface WorkflowDto {
  id: string
  name: string
  description: string
  discipline: string
  available: boolean
}

export type StandardsBrowseNodeKind = 'group' | 'node' | 'table' | 'workflow'

export interface StandardsBrowseNodeDto {
  id: string
  kind: StandardsBrowseNodeKind
  label: string
  description?: string | null
  node_id?: string | null
  workflow_id?: string | null
  content_kind?: 'node' | 'table' | null
  table_id?: string | null
  related_workflows?: WorkflowDto[]
  children?: StandardsBrowseNodeDto[]
}

export interface StandardsBrowseDto {
  standard: string
  standard_slug: string
  revision_year?: number | null
  tree: StandardsBrowseNodeDto[]
  workflow_index: Record<string, WorkflowDto[]>
}

export interface ProjectDto {
  id: string
  name: string
  task_count: number
  updated_at: string
  active_task_id?: string | null
}

export interface ProjectActivateResponse {
  project: ProjectDto
  session_id: string
}

export interface ProgressStepDto {
  id: string
  title: string
  status: 'done' | 'active' | 'pending'
  value: unknown
  unit: string | null
  display_value?: string | null
  hint?: string | null
  editable?: boolean
  provenance?: import('@/types/backend/api').NodeProvenanceDto
}

export interface ParameterEditImpactDto {
  parameter: string
  affects_path: boolean
  affects_design: boolean
  downstream_parameters: string[]
  message?: string | null
}

export interface EditSessionDto {
  parameter: string
  affects_design?: boolean
  affects_path?: boolean
  message?: string | null
}

export interface ActiveNodeContextDto {
  node_id: string
  standard: string
  paragraph?: string | null
  paragraph_number?: string | null
  equation_number?: string | null
  display_heading: string
  hover_excerpt: string
  source_field?: string | null
}

export interface NodeProvenanceDto {
  node_id: string
  title?: string | null
  standard?: string
  paragraph?: string | null
  paragraph_number?: string | null
  hover_excerpt: string
  source_field?: string | null
  generated_by?: string | null
  consumed_by?: string[]
}

export interface NodeSourceDto {
  node_id: string
  title: string
  standard: string
  paragraph?: string | null
  paragraph_number?: string | null
  equation_number?: string | null
  section?: string | null
  subsection_id?: string | null
  subsection_title?: string | null
  subsection_paragraph?: string | null
  revision_year?: number | null
  body: string
  hover_excerpt: string
}

export interface TableSourceColumnDto {
  key: string
  label: string
}

export interface TableSourceDto {
  table_id: string
  table_number?: string | null
  paragraph_number?: string | null
  title: string
  description?: string | null
  standard: string
  revision_year?: number | null
  source_path?: string | null
  columns: TableSourceColumnDto[]
  rows: Record<string, unknown>[]
  hover_excerpt: string
}

export interface NodeCalculationInputDto {
  symbol: string
  name: string
  value: string
  unit: string
}

export interface NodeCalculationSummaryDto {
  node_id: string
  paragraph?: string | null
  title: string
  primary_result: {
    symbol: string
    label: string
    value: string
    unit: string
  }
  inputs: NodeCalculationInputDto[]
}

export interface CurrentAskDto {
  kind: 'input' | 'clarify' | 'waiting'
  parameter_id?: string | null
  prompt?: string | null
}

export interface WorkflowDisplayDto {
  workflow_id: string
  display_title: string
  subtitle?: string
  standard_ref?: string
}

export interface TaskStateDto {
  task_id: string
  name: string
  workflow_id: string
  workflow_display?: WorkflowDisplayDto
  discipline: string
  description: string
  status: string
  active_nodes: string[]
  progress: {
    timeline: ProgressStepDto[]
    steps: ProgressStepDto[]
    completed_count?: number
    total_count?: number
    current_step_id?: string | null
    missing_inputs: string[]
    missing_assumptions: string[]
    submittable_parameters?: string[]
    step_progress: Array<{ step_id: string; status: string; result: unknown }>
  }
  facts: Record<string, unknown>
  /** @deprecated Use legacy_goal_map */
  goals?: Record<string, unknown>
  legacy_goal_map?: Record<string, unknown>
  execution_context?: Record<string, unknown>
  authority_context?: Record<string, unknown>
  outputs: Record<string, unknown>
  warnings: string[]
  parameters: ParameterDefinitionDto[]
  node_calculations?: NodeCalculationSummaryDto[]
  display_outputs: DisplayOutputBlock[]
  active_node_context?: ActiveNodeContextDto | null
  current_ask?: CurrentAskDto | null
  options: {
    available_workflows?: WorkflowDto[]
  }
  errors: ApiErrorBody[]
  /** Layered canonical task state (preferred for new code). */
  canonical?: CanonicalTaskStateDto
  /** Compact inspector summary derived from canonical state. */
  inspector_summary?: TaskInspectorSummaryDto
  workflow_state?: Record<string, unknown>
  /** Normalized engineering plan (source of truth). */
  engineering_plan?: EngineeringPlanDto | null
  /** Human-readable engineering plan for UI panels. */
  engineering_plan_view?: EngineeringPlanViewDto | null
  /** Dev-only performance trace for the latest interaction (when inspection enabled). */
  performance_trace?: PerformanceTraceDto
  /** Flow Guidance Layer payload (presentation blocks + active prompt). */
  flow_guidance?: {
    presentation_blocks?: unknown[]
    transcript_blocks?: unknown[]
    active_prompt?: {
      block_id?: string
      kind?: string
      source?: string
      text?: string | null
      payload?: { parameter_id?: string | null }
      refs?: Record<string, string>
    }
  }
}

export interface EngineeringValueDto {
  name: string
  value: number | string | boolean | null
  unit: string | null
  canonical_value?: number | string | boolean | null
  canonical_unit?: string | null
  dimension?: string | null
  symbol?: string | null
  source: string
  status: string
  display_value?: string | null
  parameter_node_id?: string | null
}

export interface CanonicalTaskStateDto {
  task: {
    id: string
    workflow_id: string
    name?: string
    status: string
  }
  execution: {
    phase?: string
    active_definition_node_id?: string
    current_execution_node_id?: string | null
    current_blocker?: {
      type: string
      field?: string
      parameter_node_id?: string
      message?: string
    }
  }
  values: Record<string, EngineeringValueDto>
  progress: {
    current_step_id?: string
    completed_count: number
    total_count: number
    steps: ProgressStepDto[]
    missing_inputs: string[]
    missing_assumptions: string[]
    submittable_parameters: string[]
  }
  graph: {
    selected_branch_decisions: Record<string, { field: string; value: string; selected_node: string }>
    expanded_node_ids: string[]
    active_node_ids: string[]
    resolved_node_ids: string[]
    pending_node_ids: string[]
    selected_subgraph_node_ids: string[]
  }
  lookup_results: Record<string, unknown>
  debug?: {
    warnings?: string[]
    invariant_violations?: string[]
  }
}

export interface TaskInspectorSummaryDto {
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

export interface TaskListResponse {
  session_id: string
  active_task_id: string | null
  tasks: TaskSummaryDto[]
  recent_tasks: TaskSummaryDto[]
}

export interface RecentTasksResponse {
  recent_tasks: TaskSummaryDto[]
}

export function mapBackendStatus(status: string): TaskStatus {
  switch (status) {
    case 'completed':
      return 'completed'
    case 'awaiting_input':
    case 'active':
    case 'in_progress':
      return 'in_progress'
    case 'available':
      return 'available'
    default:
      return 'in_progress'
  }
}
