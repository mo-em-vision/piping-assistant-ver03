export type TaskStatus = 'available' | 'in_progress' | 'completed'

export interface TaskSummary {
  id: string
  name: string
  description: string
  discipline: string
  status?: TaskStatus
  projectId?: string
  projectName?: string
}

export interface ProjectSummary {
  id: string
  name: string
  taskCount: number
  updatedAt: string
}
