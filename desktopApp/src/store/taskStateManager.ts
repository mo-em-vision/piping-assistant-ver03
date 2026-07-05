import type { ProgressStepDto, TaskStateDto } from '@/types/backend/api'
import type {
  StatusVariant,
  TaskStateViewModel,
  TimelineStepStatus,
  TimelineStepViewModel,
} from '@/types/frontend/taskState'
import { formatEngineeringDisplayValue } from '@/utils/engineeringDisplay'

function mapStepStatus(status: string): TimelineStepStatus {
  if (status === 'done' || status === 'active' || status === 'pending') {
    return status
  }
  return 'pending'
}

function mapStepDto(step: ProgressStepDto): TimelineStepViewModel {
  const displayValue =
    step.display_value ??
    (step.value != null ? formatEngineeringDisplayValue(step.value, step.unit) : null)

  return {
    id: step.id,
    title: step.title,
    status: mapStepStatus(step.status),
    displayValue: displayValue ?? null,
    hint: step.hint ?? null,
    editable: Boolean(step.editable),
    provenance: step.provenance,
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'completed':
      return 'Completed'
    case 'awaiting_input':
      return 'Awaiting input'
    case 'active':
      return 'Active'
    case 'paused':
      return 'Paused'
    case 'invalidated':
      return 'Invalidated'
    default:
      return status.replace(/_/g, ' ')
  }
}

function statusVariant(status: string): StatusVariant {
  switch (status) {
    case 'completed':
      return 'success'
    case 'awaiting_input':
      return 'warning'
    case 'active':
    case 'in_progress':
      return 'info'
    case 'invalidated':
      return 'error'
    default:
      return 'neutral'
  }
}

export function buildTaskStateViewModel(state: TaskStateDto | null): TaskStateViewModel | null {
  if (!state) {
    return null
  }

  const rawTimeline = state.progress.timeline ?? state.progress.steps ?? []
  const timeline = rawTimeline.map(mapStepDto)

  const completedCount = state.progress.completed_count ?? timeline.filter((s) => s.status === 'done').length
  const totalCount = state.progress.total_count ?? timeline.length
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  const currentStepId = state.progress.current_step_id ?? timeline.find((s) => s.status === 'active')?.id ?? null
  const currentStep = timeline.find((step) => step.id === currentStepId) ?? timeline.find((s) => s.status === 'active') ?? null

  return {
    statusLabel: statusLabel(state.status),
    statusVariant: statusVariant(state.status),
    progressPercent,
    completedCount,
    totalCount,
    currentStepId,
    currentStep,
    timeline,
    warnings: state.warnings ?? [],
  }
}

export function isReportSectionVisible(
  timeline: TimelineStepViewModel[],
  state?: TaskStateDto | null,
): boolean {
  if (isTaskCompleted(state)) {
    return true
  }

  return timeline.some(
    (step) =>
      (step.status === 'active' || step.status === 'done') &&
      typeof step.hint === 'string' &&
      step.hint.toLowerCase().includes('report'),
  )
}

export function isTaskCompleted(state: TaskStateDto | null | undefined): boolean {
  return state?.status === 'completed'
}
