import type {
  ProjectDto,
  TaskListResponse,
  TaskStateDto,
  TaskSummaryDto,
  WorkflowDto,
} from '@/types/backend/api'
import { mapBackendStatus } from '@/types/backend/api'

export function parseWorkflows(payload: { workflows: WorkflowDto[] }): WorkflowDto[] {
  return payload.workflows ?? []
}

export function parseProjects(payload: { projects: ProjectDto[] }): ProjectDto[] {
  return payload.projects ?? []
}

export function parseTaskList(payload: TaskListResponse): TaskListResponse {
  return {
    session_id: payload.session_id,
    active_task_id: payload.active_task_id,
    tasks: payload.tasks ?? [],
    recent_tasks: payload.recent_tasks ?? [],
  }
}

export function parseTaskState(payload: TaskStateDto): TaskStateDto {
  return payload
}

export function workflowToSummary(workflow: WorkflowDto): TaskSummaryDto {
  return {
    id: workflow.id,
    name: workflow.name,
    description: workflow.description,
    discipline: workflow.discipline,
    workflow_id: workflow.id,
    status: workflow.available ? 'available' : 'unavailable',
  }
}

export function projectToSummary(project: ProjectDto) {
  return {
    id: project.id,
    name: project.name,
    taskCount: project.task_count,
    updatedAt: project.updated_at,
  }
}

export function toNavTaskSummary(dto: TaskSummaryDto) {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description,
    discipline: dto.discipline,
    status: mapBackendStatus(dto.status),
    projectId: dto.project_id,
    projectName: dto.project_name,
  }
}
