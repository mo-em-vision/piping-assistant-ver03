import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlannerDevPanel } from '@dev-ui/inspector/PlannerDevPanel'
import { TaskStateDevPanel } from '@dev-ui/inspector/TaskStateDevPanel'

import type { InspectionPayloadDto } from '@/types/backend/inspection'

const samplePayload: InspectionPayloadDto = {
  task_id: 'task-1',
  workflow_id: 'pipe-wall-thickness',
  execution_trace: [],
  planner_decisions: {},
  planner_inspector_summary: {
    root_goal: {
      title: 'Calculate minimum required pipe wall thickness',
      target_field: 'minimum_required_thickness',
      status: 'blocked',
    },
    current_phase: 'expansion_assumptions',
    next_input: {
      field: 'straight_pipe_section',
      label: 'Straight Pipe Section',
      phase: 'expansion_assumptions',
      expected_value_class: 'selection',
      priority: 1,
    },
    outstanding_required_inputs: [
      {
        field: 'straight_pipe_section',
        label: 'Straight Pipe Section',
        phase: 'expansion_assumptions',
        expected_value_class: 'selection',
        priority: 1,
      },
      {
        field: 'pressure_loading',
        label: 'Pressure Loading',
        phase: 'path_decisions',
        expected_value_class: 'selection',
        priority: 2,
      },
    ],
    conditional_requirements: [
      {
        field: 'allowable_stress',
        title: 'Allowable Stress',
        phase: 'coefficient_resolution',
        activation_condition: { field: 'pressure_loading', operator: 'equals', value: 'internal_pressure' },
      },
    ],
    alternatives: [],
    derived_or_lookup_values: [
      {
        field: 'allowable_stress',
        title: 'Allowable Stress',
        method: 'lookup',
        depends_on: ['material_grade', 'design_temperature'],
        status: 'missing',
        activation_status: 'conditional',
      },
    ],
    calculations: [
      {
        field: 'minimum_required_thickness',
        title: 'Minimum Required Thickness',
        depends_on: ['internal_design_gage_pressure', 'outside_diameter'],
        status: 'missing',
      },
    ],
    planner_graph_summary: {
      selected_subgraph_count: 1,
      expanded_node_count: 1,
      dependency_edge_count: 16,
      branch_decision_count: 1,
    },
    traversal_summary: {
      current_active_node_id: 'PARAM-straight-pipe-section',
      current_active_node_title: 'Straight Pipe Section',
      pending_expansion_count: 2,
      expanded_count: 1,
      unresolved_branch_decisions: ['pressure_loading'],
    },
    planner_traversal_view: {
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
      expanded_nodes: [],
      branch_decisions: [],
      recent_events: [],
    },
    warnings: [],
  },
  planning_summary: {
    goal: 'Required wall thickness',
    action: 'request_input',
    current_phase: 'parameter_gathering',
    phase_missing: { parameter_gathering: ['internal_design_gage_pressure'] },
    selected_nodes: ['302.3.5-e'],
  },
  provenance_index: [],
  provenance_warnings: [],
  workflow_state: {
    current_node: 'PARAM-internal-design-gage-pressure',
    visited_nodes: ['304.1.1-a', '302.3.5-e'],
  },
  inspector_summary: {
    status: 'awaiting_input',
    phase: 'parameter_gathering',
    current_blocker: {
      type: 'missing_input',
      field: 'internal_design_gage_pressure',
      parameter_node_id: 'PARAM-internal-design-gage-pressure',
    },
    resolved_inputs: [],
    missing_inputs: ['internal_design_gage_pressure'],
    selected_branch_decisions: [],
    pending_calculations: [],
    execution_graph_summary: {
      expanded_count: 1,
      active_count: 1,
      resolved_count: 0,
      pending_count: 0,
    },
    warnings: [],
  },
  execution_events: [],
  lifecycle_events: [],
  replay_frames: [
    {
      frame_index: 0,
      step_index: null,
      active_node: '302.3.5-e',
      visited_nodes: [],
      pending_nodes: ['PARAM-pressure'],
      variables: {},
      outputs: {},
      planner_state: {},
      context: {},
    },
  ],
  replay_snapshot: {},
  integrity_checks: [],
  performance: { total_duration_ms: 0, step_count: 0, by_node_ms: {} },
  breakpoint: { paused: false },
}

describe('PlannerDevPanel', () => {
  it('shows engineering-plan planner summary and traversal', () => {
    render(
      <PlannerDevPanel payload={samplePayload} selectedNodeId={null} plannerDecision={null} />,
    )
    expect(screen.getAllByText('Expansion assumptions').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Source:')).toBeInTheDocument()
    expect(screen.getByText('Next input')).toBeInTheDocument()
    expect(screen.getByText('Dependency graph summary')).toBeInTheDocument()
    expect(screen.getByText('Outstanding required inputs')).toBeInTheDocument()
    expect(screen.getByText('Conditional future requirements')).toBeInTheDocument()
    expect(screen.getByText('Derived / lookup requirements')).toBeInTheDocument()
    expect(screen.getByText('Calculations')).toBeInTheDocument()
    expect(screen.getAllByText(/Straight Pipe Section/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Traversal summary')).toBeInTheDocument()
    expect(screen.getByText('Planner traversal')).toBeInTheDocument()
    expect(screen.queryByText('Waiting for user input')).not.toBeInTheDocument()
    expect(screen.queryByText('Parameter gathering')).not.toBeInTheDocument()
  })
})

describe('TaskStateDevPanel', () => {
  it('shows compact summary by default', () => {
    render(<TaskStateDevPanel payload={samplePayload} activeTaskState={null} />)
    expect(screen.getByText('Task status')).toBeInTheDocument()
    expect(screen.getByText('internal_design_gage_pressure')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Raw State' })).toBeInTheDocument()
    expect(screen.queryByText('Inspection payload')).not.toBeInTheDocument()
  })
})
