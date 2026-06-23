import type { TaskStateDto } from '@/types/backend/api'

/** MOCK_DATA — sample backend task state for Phase 4 visualization in mock mode. */
export const mockTaskState: TaskStateDto = {
  task_id: 'mock-pipe-thickness',
  name: 'Pipe Thickness Calculation',
  workflow_id: 'pipe_wall_thickness_design',
  discipline: 'Piping',
  description: 'ASME B31.3 wall thickness design',
  status: 'awaiting_input',
  active_nodes: ['B313-material-stress', 'B313-304.1.1'],
  progress: {
    timeline: [
      {
        id: 'material',
        title: 'Material',
        status: 'done',
        value: 'SA-106B',
        unit: 'dimensionless',
        display_value: 'SA-106B',
      },
      {
        id: 'design_pressure',
        title: 'Pressure',
        status: 'done',
        value: 8,
        unit: 'bar',
        display_value: '8 bar',
      },
      {
        id: 'thickness',
        title: 'Thickness',
        status: 'active',
        value: null,
        unit: null,
        hint: 'Waiting for thickness calculation',
      },
      {
        id: 'report',
        title: 'Report',
        status: 'pending',
        value: null,
        unit: null,
        hint: 'Available after calculation completes',
      },
    ],
    steps: [],
    completed_count: 2,
    total_count: 4,
    current_step_id: 'thickness',
    missing_inputs: ['nominal_pipe_size'],
    missing_assumptions: [],
    step_progress: [],
  },
  inputs: {
    material: {
      input_id: 'material',
      value: 'SA-106B',
      unit: 'dimensionless',
      display_value: 'SA-106B',
    },
    design_pressure: {
      input_id: 'design_pressure',
      value: 8,
      unit: 'bar',
      display_value: '8 bar',
    },
  },
  outputs: {
    workflow: 'pipe_wall_thickness_design',
    planning_summary: { action: 'request_input' },
  },
  warnings: [],
  parameters: [
    {
      name: 'nominal_pipe_size',
      label: 'Nominal Pipe Size',
      type: 'text',
      required: true,
      units: [],
      default_unit: 'dimensionless',
      default_value: null,
      value: null,
      options: null,
      validation: null,
      status: 'pending',
      requires_confirmation: false,
    },
  ],
  display_outputs: [
    {
      id: 'planning-status',
      type: 'text',
      title: 'Task status',
      content:
        'Goal: pipe wall thickness design. Waiting for inputs: nominal_pipe_size.',
      variant: 'body',
    },
    {
      id: 'preview-equation',
      type: 'equation',
      title: 'Governing equation',
      content: 't = \\frac{PD}{2(SEW + PY)}',
      display: 't = PD / 2(SEW + PY)',
      variables: [
        { symbol: 'P', name: 'Design pressure' },
        { symbol: 'D', name: 'Outside diameter' },
        { symbol: 'S', name: 'Allowable stress' },
      ],
    },
    {
      id: 'preview-reference',
      type: 'reference',
      title: 'Straight Pipe Under Internal Pressure',
      standard: 'ASME B31.3',
      paragraph: '304.1.2',
      excerpt:
        'The minimum required wall thickness for straight pipe under internal pressure shall be computed.',
      source_node: 'B313-304.1.2',
    },
  ],
  options: {},
  errors: [],
}

mockTaskState.progress.steps = mockTaskState.progress.timeline
