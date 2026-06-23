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
    step_progress: Array<{ step_id: string; status: string; result: unknown }>
  }
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  warnings: string[]
  parameters: ParameterDefinitionDto[]
  display_outputs: DisplayOutputBlock[]
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
