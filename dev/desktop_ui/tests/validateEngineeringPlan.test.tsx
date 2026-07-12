import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { validateEngineeringPlan } from '@dev-ui/inspector/validateEngineeringPlan'

import type { EngineeringPlanDto } from '@/types/backend/inspection'

const minimalValidPlan = {
  plan_id: 'PLAN-test',
  task_id: 'task-1',
  workflow_id: 'pipe_wall_thickness_design',
  root_goal: {
    id: 'GOAL-calculate-minimum-required-thickness',
    key: 'calculate-minimum-required-thickness',
    title: 'Calculate minimum required pipe wall thickness',
    goal_class: 'calculation_goal' as const,
    target_parameter: 'PARAM-minimum-required-thickness',
    target_field: 'minimum_required_thickness',
    status: 'blocked',
    blocked_by: ['REQ-straight_pipe_section', 'REQ-pressure_loading'],
    required_outputs: [],
  },
  requirements: {
    'REQ-straight_pipe_section': {
      id: 'REQ-straight_pipe_section',
      key: 'input-straight_pipe_section',
      field: 'straight_pipe_section',
      title: 'Straight Pipe Section',
      parameter_node_id: 'PARAM-straight-pipe-section',
      requirement_class: 'user_input',
      status: 'missing',
      phase: 'expansion_assumptions',
      required_by: [],
      depends_on: [],
    },
    'REQ-pressure_loading': {
      id: 'REQ-pressure_loading',
      key: 'input-pressure_loading',
      field: 'pressure_loading',
      title: 'Pressure Loading',
      parameter_node_id: 'PARAM-pressure-loading',
      requirement_class: 'branch_decision',
      status: 'missing',
      phase: 'path_decisions',
      required_by: [],
      depends_on: ['REQ-straight_pipe_section'],
    },
    'REQ-diameter_resolution': {
      id: 'REQ-diameter_resolution',
      key: 'input-outside_diameter',
      field: 'outside_diameter',
      title: 'Pipe diameter',
      parameter_node_id: 'PARAM-outside-diameter',
      requirement_class: 'user_input',
      status: 'missing',
      phase: 'parameter_gathering',
      required_by: [],
      depends_on: [],
      alternatives: [
        {
          id: 'ALT-direct-outside-diameter',
          label: 'Direct',
          fields: ['outside_diameter'],
          resolves: 'outside_diameter',
          method: 'direct_input',
        },
        {
          id: 'ALT-nps-lookup',
          label: 'NPS',
          fields: ['nominal_pipe_size'],
          resolves: 'outside_diameter',
          method: 'lookup',
        },
      ],
    },
    'REQ-internal_design_gage_pressure': {
      id: 'REQ-internal_design_gage_pressure',
      key: 'input-internal_design_gage_pressure',
      field: 'internal_design_gage_pressure',
      title: 'Internal Design Gage Pressure',
      parameter_node_id: 'PARAM-internal-design-gage-pressure',
      requirement_class: 'user_input',
      status: 'missing',
      phase: 'parameter_gathering',
      required_by: [],
      depends_on: [],
      activation_status: 'conditional',
    },
    'REQ-allowable_stress_lookup': {
      id: 'REQ-allowable_stress_lookup',
      key: 'lookup-allowable_stress',
      field: 'allowable_stress',
      title: 'Allowable Stress',
      parameter_node_id: 'PARAM-allowable-stress',
      requirement_class: 'table_lookup',
      status: 'missing',
      phase: 'coefficient_resolution',
      required_by: [],
      depends_on: [],
    },
    'REQ-basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes_lookup': {
      id: 'REQ-basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes_lookup',
      key: 'lookup-basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes',
      field: 'basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes',
      title: 'Basic Quality Factors for Longitudinal Weld Joints in Pipes and Tubes',
      parameter_node_id: 'PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes',
      requirement_class: 'table_lookup',
      status: 'missing',
      phase: 'coefficient_resolution',
      required_by: [],
      depends_on: [],
    },
    'REQ-temperature_coefficient_Y_lookup': {
      id: 'REQ-temperature_coefficient_Y_lookup',
      key: 'lookup-temperature_coefficient_Y',
      field: 'temperature_coefficient_Y',
      title: 'Temperature Coefficient Y',
      parameter_node_id: 'PARAM-temperature-coefficient-Y',
      requirement_class: 'table_lookup',
      status: 'missing',
      phase: 'coefficient_resolution',
      required_by: [],
      depends_on: [],
    },
    'REQ-weld_strength_reduction_factor_W_lookup': {
      id: 'REQ-weld_strength_reduction_factor_W_lookup',
      key: 'lookup-weld_strength_reduction_factor_W',
      field: 'weld_strength_reduction_factor_W',
      title: 'Weld Strength Reduction Factor W',
      parameter_node_id: 'PARAM-weld-strength-reduction-factor-W',
      requirement_class: 'table_lookup',
      status: 'missing',
      phase: 'coefficient_resolution',
      required_by: [],
      depends_on: [],
    },
    'REQ-metallurgical_group_lookup': {
      id: 'REQ-metallurgical_group_lookup',
      key: 'lookup-metallurgical_group',
      field: 'metallurgical_group',
      title: 'Metallurgical Group',
      parameter_node_id: 'PARAM-metallurgical-group',
      requirement_class: 'table_lookup',
      status: 'missing',
      phase: 'coefficient_resolution',
      required_by: [],
      depends_on: [],
    },
    'REQ-required_wall_thickness': {
      id: 'REQ-required_wall_thickness',
      key: 'equation-required_wall_thickness',
      field: 'required_wall_thickness',
      title: 'Required Wall Thickness',
      parameter_node_id: null,
      requirement_class: 'equation_result',
      status: 'missing',
      phase: 'equation_execution',
      required_by: [],
      depends_on: [],
    },
    'REQ-minimum_required_thickness_eq': {
      id: 'REQ-minimum_required_thickness_eq',
      key: 'equation-minimum_required_thickness',
      field: 'minimum_required_thickness',
      title: 'Minimum Required Thickness',
      parameter_node_id: null,
      requirement_class: 'equation_result',
      status: 'missing',
      phase: 'equation_execution',
      required_by: [],
      depends_on: [],
    },
  },
  dependencies: [{ from: 'REQ-straight_pipe_section', to: 'REQ-pressure_loading', type: 'requires' }],
  input_strategy: {
    mode: 'single_next_question',
    current_phase: 'expansion_assumptions',
    next_fields: ['straight_pipe_section'],
    blocked_fields: [],
    resolved_fields: [],
  },
  phases: [{ id: 'expansion_assumptions', title: 'Expansion assumptions', order: 0, requirement_ids: [], status: 'active' }],
  graph: {
    selected_subgraph_node_ids: ['WF-PIPE-WALL-THICKNESS'],
    selected_branch_decisions: [],
    expanded_node_ids: ['WF-PIPE-WALL-THICKNESS'],
  },
  traversal: {
    traversal_id: 'TRAV-test',
    current_active_node_id: 'PARAM-straight-pipe-section',
    current_active_node: {
      node_id: 'PARAM-straight-pipe-section',
      node_type: 'parameter',
      title: 'Straight Pipe Section',
      phase: 'expansion_assumptions',
      reason: 'Required to confirm whether straight pipe thickness rules apply.',
    },
    pending_expansion_nodes: [
      {
        node_id: 'PARAM-pressure-loading',
        node_type: 'parameter',
        title: 'Pressure Loading',
        phase: 'path_decisions',
        waiting_on: ['PARAM-straight-pipe-section'],
        reason: 'Pressure branch cannot be selected until expansion assumptions are resolved.',
      },
    ],
    expanded_nodes: [
      {
        node_id: 'WF-PIPE-WALL-THICKNESS',
        node_type: 'workflow',
        title: 'Pipe Wall Thickness Workflow',
        expanded_at_order: 1,
        produced_requirements: ['REQ-straight_pipe_section', 'REQ-pressure_loading'],
        produced_edges: [],
      },
    ],
    branch_decisions: [
      {
        field: 'pressure_loading',
        value: null,
        selected_node: null,
        candidate_nodes: ['304.1.2-a', '304.1.3'],
        status: 'unresolved' as const,
      },
    ],
    traversal_events: [],
  },
} satisfies EngineeringPlanDto

describe('validateEngineeringPlan', () => {
  it('accepts a normalized engineering plan shape', () => {
    const result = validateEngineeringPlan(minimalValidPlan)
    expect(result.valid).toBe(true)
    expect(result.errors).toEqual([])
  })

  it('rejects a flat legacy goal map', () => {
    const legacy = {
      'GOAL-calculate-minimum-required-thickness': { key: 'calculate-minimum-required-thickness' },
      'REQ-straight_pipe_section': { key: 'input-straight_pipe_section' },
    }
    const result = validateEngineeringPlan(legacy)
    expect(result.valid).toBe(false)
    expect(result.errors[0]).toMatch(/flat top-level GOAL-\*\/REQ-\* map/)
  })
})

describe('PlannerDevPanel blocked reason section', () => {
  it('renders blocked reason from projection only', async () => {
    const { PlannerDevPanel } = await import('@dev-ui/inspector/PlannerDevPanel')
    render(
      <PlannerDevPanel
        projection={{
          workflow_title: 'Test Workflow',
          workflow_slug: 'test_workflow',
          planner_confidence: null,
          planner_reason: null,
          current_step: {
            phase: 'parameter_gathering',
            phase_label: 'Parameter gathering',
            status_badge: 'waiting_for_input',
          },
          active_node: null,
          visited_timeline: [],
          pending_nodes: [],
          pending_calculations: [],
          pending_validations: [],
          pending_lookups: [],
          required_inputs: [],
          blocked_reason: {
            kind: 'not_available',
            message: 'Insufficient plan evidence to classify blocker',
            missing_item: null,
          },
          next_expected_action: null,
          warnings: ['Plan warning example'],
          raw_planner_state: {
            engineering_plan: minimalValidPlan,
            planner_inspector_summary: {},
          },
        }}
      />,
    )
    expect(screen.getByText('Blocked / Waiting Reason')).toBeInTheDocument()
    expect(screen.getByText('Plan warning example')).toBeInTheDocument()
    expect(screen.queryByText('Valid normalized engineering plan.')).not.toBeInTheDocument()
  })
})
