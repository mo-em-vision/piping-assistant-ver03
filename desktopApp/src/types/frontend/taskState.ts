export type TimelineStepStatus = 'done' | 'active' | 'pending'

export type StatusVariant = 'success' | 'warning' | 'info' | 'neutral' | 'error'

export interface TimelineStepViewModel {
  id: string
  title: string
  status: TimelineStepStatus
  displayValue: string | null
  hint: string | null
}

export interface TaskStateViewModel {
  statusLabel: string
  statusVariant: StatusVariant
  progressPercent: number
  completedCount: number
  totalCount: number
  currentStepId: string | null
  currentStep: TimelineStepViewModel | null
  timeline: TimelineStepViewModel[]
  warnings: string[]
}
