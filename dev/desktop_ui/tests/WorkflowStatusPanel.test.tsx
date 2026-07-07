import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlannerDevPanel } from '@dev-ui/inspector/PlannerDevPanel'
import { PlannerTraversalTimeline } from '@dev-ui/inspector/PlannerTraversalTimeline'
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
    current_phase_inputs: [
      {
        field: 'straight_pipe_section',
        label: 'Straight Pipe Section',
        phase: 'expansion_assumptions',
        expected_value_class: 'selection',
        priority: 1,
      },
    ],
    future_phase_inputs: [
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
    traversal_path: [
      {
        node_id: 'PARAM-straight-pipe-section',
        title: 'Straight Pipe Section',
        node_type: 'parameter',
        state: 'current',
        reason: 'Required to confirm whether straight pipe thickness rules apply.',
        waiting_on: [],
      },
      {
        node_id: 'PARAM-pressure-loading',
        title: 'Pressure Loading',
        node_type: 'parameter',
        state: 'blocked',
        reason: 'Pressure branch cannot be selected until expansion assumptions are resolved.',
        waiting_on: ['PARAM-straight-pipe-section'],
      },
    ],
    header: {
      workflow_id: 'pipe_wall_thickness_design',
      workflow_name: 'Pipe Wall Thickness Design',
      current_phase: 'expansion_assumptions',
      current_phase_label: 'Expansion assumptions',
      current_active_node_id: 'PARAM-straight-pipe-section',
      current_active_node_title: 'Straight Pipe Section',
      next_action: { field: 'straight_pipe_section', label: 'Straight Pipe Section' },
      status_badge: 'waiting_for_input',
      why_here: 'Required to confirm whether straight pipe thickness rules apply.',
      traversal_support_level: 'full',
      traversal_support_note: null,
    },
    phase_panel: {
      current_phase: 'expansion_assumptions',
      current_phase_label: 'Expansion assumptions',
      active_field: 'straight_pipe_section',
      completed_fields: [],
      missing_in_phase: [],
      future_fields: [
        {
          field: 'pressure_loading',
          label: 'Pressure Loading',
          phase: 'path_decisions',
          expected_value_class: 'selection',
          priority: 2,
        },
      ],
    },
    requirements_panel: [
      {
        id: 'conditional-allowable_stress',
        field: 'allowable_stress',
        label: 'Allowable Stress',
        category: 'conditional',
        resolution_kind: 'conditional',
        display_status: 'pending',
        awaiting_user_input: false,
        resolution_label: 'Conditional — not user input',
        depends_on: [],
        source_node_id: null,
        phase: 'coefficient_resolution',
      },
      {
        id: 'lookup-allowable_stress',
        field: 'allowable_stress',
        label: 'Allowable Stress',
        category: 'lookup_derived',
        resolution_kind: 'table_lookup',
        display_status: 'pending',
        awaiting_user_input: false,
        resolution_label: 'Lookup-derived',
        depends_on: ['material_grade', 'design_temperature'],
        source_node_id: 'LOOKUP-allowable-stress',
        phase: null,
      },
    ],
    planner_traversal_view: {
      current_active_node: {
        node_id: 'PARAM-straight-pipe-section',
        node_type: 'parameter',
        title: 'Straight Pipe Section',
        phase: 'expansion_assumptions',
        reason: 'Required to confirm whether straight pipe thickness rules apply.',
      },
      pending_expansion_nodes: [],
      expanded_nodes: [],
      branch_decisions: [],
      recent_events: [],
    },
    warnings: [],
  },
  planning_summary: {},
  provenance_index: [],
  provenance_warnings: [],
  workflow_state: {},
  task_state_views: {
    state_summary: {
      task_id: 'task-1',
      task_name: 'task-1',
      status: 'awaiting_input',
      workflow_id: 'pipe_wall_thickness_design',
      selected_root: 'pipe_wall_thickness_design',
      current_phase: 'parameter_gathering',
      readiness: 'waiting_for_input',
      expanded_node_count: 1,
      missing_input_count: 1,
    },
    facts_view: [
      {
        field: 'internal_design_gage_pressure',
        label: 'Internal Design Gage Pressure',
        symbol: 'P',
        value: null,
        unit: 'bar',
        source: 'user_input',
        status: 'missing',
        parameter_node_id: 'PARAM-internal-design-gage-pressure',
      },
    ],
    decisions_view: [],
    outputs_view: [],
    validation_view: {
      status: 'ok',
      errors: [],
      warnings: [],
      overrides: [],
      conflicts: [],
      affected_nodes: [],
    },
    trace_timeline: [
      {
        order: 1,
        event_type: 'input_requested',
        label: 'Input requested',
        node_id: 'PARAM-internal-design-gage-pressure',
        message: 'Field: internal_design_gage_pressure',
        source: 'execution',
      },
    ],
  },
  execution_events: [],
  lifecycle_events: [],
  replay_frames: [],
  replay_snapshot: {},
  integrity_checks: [],
  performance: { total_duration_ms: 0, step_count: 0, by_node_ms: {} },
  breakpoint: { paused: false },
}

describe('PlannerDevPanel', () => {
  it('shows human-friendly planner sections without raw JSON in default view', () => {
    render(
      <PlannerDevPanel payload={samplePayload} selectedNodeId={null} plannerDecision={null} />,
    )
    expect(screen.getByText('Pipe Wall Thickness Design')).toBeInTheDocument()
    expect(screen.getByText('Waiting for input')).toBeInTheDocument()
    expect(screen.getByText('Traversal path')).toBeInTheDocument()
    expect(screen.getByText('Inspector debug')).toBeInTheDocument()
    expect(screen.getByText(/Developer \/ debug view only/)).toBeInTheDocument()
    expect(screen.getByText('Planner phase details')).toBeInTheDocument()
    expect(screen.queryByText('engineering_plan')).not.toBeInTheDocument()
    expect(screen.getByText('Advanced / Raw Data — Canonical engineering plan')).toBeInTheDocument()
  })
})

describe('PlannerTraversalTimeline', () => {
  it('renders completed current blocked and skipped rows', () => {
    render(
      <PlannerTraversalTimeline
        rows={[
          { node_id: 'n1', title: 'Done', node_type: 'paragraph', state: 'completed', waiting_on: [] },
          { node_id: 'n2', title: 'Now', node_type: 'parameter', state: 'current', waiting_on: [] },
          { node_id: 'n3', title: 'Blocked', node_type: 'parameter', state: 'blocked', waiting_on: ['n2'], reason: 'waiting' },
          { node_id: 'n4', title: 'Skipped', node_type: 'paragraph', state: 'skipped', waiting_on: [], reason: 'not applicable' },
        ]}
      />,
    )
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(screen.getByText('Now')).toBeInTheDocument()
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Skipped')).toBeInTheDocument()
    expect(screen.getByText('Waiting on: n2')).toBeInTheDocument()
  })

  it('shows limited traversal support note when empty', () => {
    render(
      <PlannerTraversalTimeline
        rows={[]}
        supportLevel="none"
        supportNote="Traversal timeline is only built for pipe wall thickness workflows today."
      />,
    )
    expect(screen.getByText(/pipe wall thickness workflows today/i)).toBeInTheDocument()
    expect(screen.getByText(/Traversal timeline support/i)).toBeInTheDocument()
  })
})

describe('TaskStateDevPanel', () => {
  it('shows structured task state panels without raw JSON in default view', () => {
    render(<TaskStateDevPanel payload={samplePayload} activeTaskState={null} />)
    expect(screen.getByText('Facts / inputs')).toBeInTheDocument()
    expect(screen.getByText(/Developer \/ debug view only/)).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Raw State' })).not.toBeInTheDocument()
    expect(screen.getByText('Advanced / Raw Data — Canonical task state')).toBeInTheDocument()
  })
})
