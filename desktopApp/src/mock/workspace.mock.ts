import type { ProjectSummary, TaskSummary } from '@/types/frontend/workspace'

/** MOCK_DATA — replace with backend API responses in Phase 3+. */
export const mockAvailableTasks: TaskSummary[] = [
  {
    id: 'pipe_wall_thickness',
    name: 'Pipe Thickness Calculation',
    description: 'ASME B31.3 wall thickness design workflow',
    discipline: 'Piping',
  },
  {
    id: 'flange_selection',
    name: 'Flange Selection',
    description: 'Select flanges for piping systems',
    discipline: 'Piping',
  },
  {
    id: 'material_selection',
    name: 'Material Selection',
    description: 'Choose materials from standards databases',
    discipline: 'Materials',
  },
  {
    id: 'tank_design',
    name: 'Tank Design',
    description: 'API 650 storage tank design workflow',
    discipline: 'Mechanical',
  },
  {
    id: 'standards_lookup',
    name: 'Standards Lookup',
    description: 'Search and navigate engineering standards',
    discipline: 'Reference',
  },
]

export const mockRecentTasks: TaskSummary[] = [
  {
    id: 'recent_pipe_001',
    name: 'Pipe Thickness — Line 200',
    description: '8 bar design pressure, SA-106B',
    discipline: 'Piping',
    status: 'in_progress',
    projectId: 'proj_refinery',
    projectName: 'Refinery Expansion',
  },
  {
    id: 'recent_material_002',
    name: 'Material Selection — SS piping',
    description: 'TP316L for corrosive service',
    discipline: 'Materials',
    status: 'completed',
    projectId: 'proj_offshore',
    projectName: 'Offshore Platform B',
  },
]

export const mockProjects: ProjectSummary[] = [
  {
    id: 'proj_refinery',
    name: 'Refinery Expansion',
    taskCount: 4,
    updatedAt: '2026-06-20',
  },
  {
    id: 'proj_offshore',
    name: 'Offshore Platform B',
    taskCount: 2,
    updatedAt: '2026-06-18',
  },
]
