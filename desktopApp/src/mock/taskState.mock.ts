import type { TaskStateDto } from '@/types/backend/api'

/** MOCK_DATA — sample backend task state for Phase 4 visualization in mock mode. */
export const mockTaskState: TaskStateDto = {
  task_id: 'mock-pipe-thickness',
  name: 'Pipe Thickness Calculation',
  workflow_id: 'pipe_wall_thickness_design',
  discipline: 'Piping',
  description: 'ASME B31.3 wall thickness design',
  status: 'awaiting_input',
  active_nodes: ['B313-table-A-1', 'B313-304.1.1'],
  progress: {
    timeline: [
      {
        id: 'straight_pipe_section',
        title: 'Straight pipe section',
        status: 'done',
        value: true,
        unit: 'dimensionless',
        display_value: 'Yes',
      },
      {
        id: 'pressure_loading',
        title: 'Pressure loading',
        status: 'done',
        value: 'internal_pressure',
        unit: 'dimensionless',
        display_value: 'The pipe is internally pressurized.',
      },
      {
        id: 'internal_design_gage_pressure',
        title: 'Internal design gage pressure',
        status: 'done',
        value: 8,
        unit: 'bar',
        display_value: '8 bar',
      },
      {
        id: 'nominal_pipe_size',
        title: 'Nominal pipe size',
        status: 'active',
        value: null,
        unit: null,
        hint: 'Waiting for nominal pipe size',
      },
      {
        id: 'material_grade',
        title: 'Material Grade',
        status: 'done',
        value: 'astm_a106_gr_b',
        unit: 'dimensionless',
        display_value: 'ASTM A106 Grade B',
      },
      {
        id: 'thickness',
        title: 'Thickness',
        status: 'pending',
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
    completed_count: 4,
    total_count: 7,
    current_step_id: 'nominal_pipe_size',
    missing_inputs: ['nominal_pipe_size'],
    missing_assumptions: [],
    submittable_parameters: ['nominal_pipe_size'],
    step_progress: [],
  },
  facts: {
    material_grade: {
      id: 'FACT-mock-material',
      key: 'material_grade',
      parameter: 'PARAM-material-grade',
      value: { label: 'astm_a106_gr_b' },
      display_value: 'ASTM A106 Grade B',
    },
    internal_design_gage_pressure: {
      id: 'FACT-mock-pressure',
      key: 'internal_design_gage_pressure',
      parameter: 'PARAM-internal-design-gage-pressure',
      value: { amount: 8, unit: 'UNIT-bar' },
      display_value: '8 bar',
    },
  },
  outputs: {
    workflow: 'pipe_wall_thickness_design',
  },
  goals: {},
  warnings: [],
  parameters: [
    {
      name: 'nominal_pipe_size',
      label: 'Nominal Pipe Size',
      type: 'dropdown',
      required: true,
      units: [],
      default_unit: 'NPS',
      default_value: null,
      value: null,
      options: [
        { value: '1/2', label: 'NPS 1/2' },
        { value: '2', label: 'NPS 2' },
        { value: '4', label: 'NPS 4' },
      ],
      diameter_ui: {
        input_modes: [
          { value: 'nps_lookup', label: 'NPS' },
          { value: 'direct_od', label: 'Outside diameter' },
          { value: 'direct_id', label: 'Inside diameter' },
        ],
        related_options: {
          nominal_pipe_size: [
            { value: '1/2', label: 'NPS 1/2' },
            { value: '2', label: 'NPS 2' },
            { value: '2-1/2', label: 'NPS 2-1/2' },
            { value: '4', label: 'NPS 4' },
            { value: '6', label: 'NPS 6' },
          ],
          outside_diameter: [
            { value: '60.325', label: '2.375 in (60.325 mm)' },
            { value: '114.3', label: '4.5 in (114.3 mm)' },
            { value: '168.275', label: '6.625 in (168.275 mm)' },
          ],
        },
      },
      validation: null,
      status: 'pending',
      requires_confirmation: false,
    },
  ],
  display_outputs: [
    {
      id: 'planning-status',
      type: 'text',
      title: 'Task status:',
      content: 'Complete the fields below to continue.',
      variant: 'body',
    },
    {
      id: 'preview-equation',
      type: 'equation',
      title: 'Governing equation',
      content: 't = \\frac{PD}{2(SEW + PY)}',
      display: 't = PD / 2(SEW + PY)',
      input_table: {
        columns: [
          { key: 'symbol', label: 'Symbol', sortable: false },
          { key: 'definition', label: 'Definition', sortable: false },
          { key: 'value', label: 'Value', sortable: false },
        ],
        rows: [
          { symbol: 'P', definition: 'Design pressure', value: '8 bar' },
          {
            symbol: 'D',
            definition: 'Outside diameter',
            value: 'Awaiting user input',
            definition_reference: { node_id: '304.1.1-b', label: '§304.1.1-b' },
          },
          { symbol: 'S', definition: 'Allowable stress', value: 'Awaiting user input' },
        ],
      },
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
        id: 'material_grade',
        title: 'Material Grade',
        status: 'done',
        value: 'astm_a106_gr_b',
        unit: 'dimensionless',
        display_value: 'ASTM A106 Grade B',
      },
      {
        id: 'internal_design_gage_pressure',
        title: 'Internal design gage pressure',
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
    required_thickness: 4.2,
    minimum_required_thickness: 4.2,
  },
  goals: {},
}

mockCompletedTaskState.progress.steps = mockCompletedTaskState.progress.timeline
