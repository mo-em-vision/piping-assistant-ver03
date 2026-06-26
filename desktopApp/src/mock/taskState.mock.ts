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
        value: 'astm_a106_gr_b',
        unit: 'dimensionless',
        display_value: 'ASTM A106 Grade B',
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
    submittable_parameters: ['nominal_pipe_size'],
    step_progress: [],
  },
  inputs: {
    material: {
      input_id: 'material',
      value: 'astm_a106_gr_b',
      unit: 'dimensionless',
      display_value: 'ASTM A106 Grade B',
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
      units: ['NPS', 'DN'],
      default_unit: 'NPS',
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
      id: 'preview-intro',
      type: 'text',
      content:
        'The minimum required wall thickness for straight pipe under internal pressure shall be computed based on',
      content_suffix: ' with the following equation:',
      variant: 'body',
      reference_links: [
        {
          node_id: 'B313-304.1.2',
          label: '§304.1.2',
          paragraph: '304.1.2',
        },
      ],
      reference_links_placement: 'inline',
    },
  ],
  active_node_context: {
    node_id: 'B313-304.1.1',
    standard: 'ASME B31.3',
    paragraph: '304.1.1',
    display_heading:
      'Calculation of Minimum Required Thickness of a straight section pipe (according to ASME B 31.3 paragraph 304.1.1)',
    hover_excerpt:
      'The required thickness of straight sections of pipe shall be determined in accordance with eq. (2).',
  },
  options: {},
  errors: [],
}

mockTaskState.progress.steps = mockTaskState.progress.timeline

/** MOCK_DATA — completed task state for completion next-steps UI. */
export const mockCompletedTaskState: TaskStateDto = {
  ...mockTaskState,
  status: 'completed',
  progress: {
    ...mockTaskState.progress,
    timeline: [
      {
        id: 'material',
        title: 'Material',
        status: 'done',
        value: 'astm_a106_gr_b',
        unit: 'dimensionless',
        display_value: 'ASTM A106 Grade B',
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
        status: 'done',
        value: 4.2,
        unit: 'mm',
        display_value: '4.2 mm',
      },
      {
        id: 'report',
        title: 'Report',
        status: 'done',
        value: null,
        unit: null,
        hint: 'Generate an engineering report',
      },
    ],
    completed_count: 4,
    total_count: 4,
    current_step_id: 'report',
    missing_inputs: [],
    missing_assumptions: [],
    submittable_parameters: [],
    step_progress: [],
  },
  parameters: [],
  display_outputs: [
    ...mockTaskState.display_outputs,
    {
      id: 'result-thickness',
      type: 'result',
      title: 'Required wall thickness',
      label: 'Required wall thickness',
      value: '4.2',
      unit: 'mm',
      status: 'pass',
    },
  ],
  outputs: {
    workflow: 'pipe_wall_thickness_design',
    planning_summary: { action: 'complete' },
    required_thickness: 4.2,
    minimum_required_thickness: 4.2,
  },
}

mockCompletedTaskState.progress.steps = mockCompletedTaskState.progress.timeline
