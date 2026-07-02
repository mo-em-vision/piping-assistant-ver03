import type { DisplayOutputBlock } from '@/types/backend/outputs'
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
  display_heading: string
  hover_excerpt: string
  source_field?: string | null
}

export interface NodeProvenanceDto {
  node_id: string
  title?: string | null
  standard?: string
  paragraph?: string | null
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

export interface TaskStateDto {
  task_id: string
  name: string
  workflow_id: string
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
  goals?: Record<string, unknown>
  execution_context?: Record<string, unknown>
  authority_context?: Record<string, unknown>
  outputs: Record<string, unknown>
  warnings: string[]
  parameters: ParameterDefinitionDto[]
  node_calculations?: NodeCalculationSummaryDto[]
  display_outputs: DisplayOutputBlock[]
  active_node_context?: ActiveNodeContextDto | null
  options: {
    available_workflows?: WorkflowDto[]
  }
  errors: ApiErrorBody[]
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
