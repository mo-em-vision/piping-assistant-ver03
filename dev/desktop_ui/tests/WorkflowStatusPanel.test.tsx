import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlannerDevPanel } from '@dev-ui/inspector/PlannerDevPanel'
import { PlannerTraversalTimelineSection } from '@dev-ui/inspector/PlannerTraversalTimelineSection'
import { TaskStateDevPanel } from '@dev-ui/inspector/TaskStateDevPanel'

import type { InspectionPayloadDto, PlannerDebugProjectionDto } from '@/types/backend/inspection'

const sampleProjection: PlannerDebugProjectionDto = {
  workflow_title: 'Pipe Wall Thickness Design',
  workflow_slug: 'pipe_wall_thickness_design',
  planner_confidence: null,
  planner_reason: null,
  current_step: {
    phase: 'expansion_assumptions',
    phase_label: 'Expansion assumptions',
    status_badge: 'waiting_for_input',
  },
  active_node: {
    node_id: 'PARAM-straight-pipe-section',
    title: 'Straight Pipe Section',
    node_type: 'parameter',
    why_active: 'Required to confirm whether straight pipe thickness rules apply.',
  },
  visited_timeline: [
    {
      node_id: 'WF-PIPE-WALL-THICKNESS',
      title: 'Pipe Wall Thickness Workflow',
      node_type: 'workflow',
      why_visited: null,
      status: 'visited',
      waiting_on: [],
    },
    {
      node_id: 'PARAM-straight-pipe-section',
      title: 'Straight Pipe Section',
      node_type: 'parameter',
      why_visited: 'Required to confirm whether straight pipe thickness rules apply.',
      status: 'active',
      waiting_on: [],
    },
    {
      node_id: 'PARAM-pressure-loading',
      title: 'Pressure Loading',
      node_type: 'parameter',
      why_visited: 'Pressure branch cannot be selected until expansion assumptions are resolved.',
      status: 'blocked',
      waiting_on: ['PARAM-straight-pipe-section'],
    },
  ],
  pending_nodes: [
    {
      node_id: 'PARAM-pressure-loading',
      title: 'Pressure Loading',
      node_type: 'parameter',
      reason: 'Waiting on straight pipe confirmation',
      waiting_on: ['PARAM-straight-pipe-section'],
    },
  ],
  pending_calculations: [
    {
      field: 'minimum_required_thickness',
      title: 'Minimum Required Thickness',
      status: 'missing',
      depends_on: ['internal_design_gage_pressure'],
      reason: 'Calculation missing',
    },
  ],
  pending_validations: [],
  pending_lookups: [
    {
      field: 'allowable_stress',
      title: 'Allowable Stress',
      status: 'missing',
      depends_on: ['material_grade'],
      reason: 'Lookup missing',
    },
  ],
  required_inputs: [
    {
      key: 'straight_pipe_section',
      symbol: 'straight_pipe_section',
      label: 'Straight Pipe Section',
      status: 'missing',
      expected_input_type: 'selection',
      unit: null,
      reason_required: 'expansion_assumptions',
    },
  ],
  blocked_reason: {
    kind: 'waiting_for_user_input',
    message: 'Waiting for user input: Straight Pipe Section',
    missing_item: 'straight_pipe_section',
  },
  next_expected_action: 'Collect user input for Straight Pipe Section',
  warnings: [],
  raw_planner_state: {
    engineering_plan: { plan_id: 'PLAN-test' },
    planner_inspector_summary: { root_goal: { title: 'hidden' } },
  },
}

const samplePayload: InspectionPayloadDto = {
  task_id: 'task-1',
  workflow_id: 'pipe-wall-thickness',
  execution_trace: [],
  planner_decisions: {},
  planner_debug_projection: sampleProjection,
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
  it('shows seven readable sections without raw JSON in default view', () => {
    render(<PlannerDevPanel projection={sampleProjection} />)

    expect(screen.getByText('Planner Summary')).toBeInTheDocument()
    expect(screen.getByText('Current Execution Step')).toBeInTheDocument()
    expect(screen.getByText('Traversal Timeline')).toBeInTheDocument()
    expect(screen.getByText('Pending Work')).toBeInTheDocument()
    expect(screen.getByText('Required Inputs')).toBeInTheDocument()
    expect(screen.getByText('Blocked / Waiting Reason')).toBeInTheDocument()
    expect(screen.getByText('Advanced Planner JSON')).toBeInTheDocument()

    expect(screen.getByText('Pipe Wall Thickness Design')).toBeInTheDocument()
    expect(screen.getByText('Waiting for user input')).toBeInTheDocument()
    expect(screen.getByText(/Developer \/ debug view only/)).toBeInTheDocument()
    expect(screen.queryByText('PLAN-test')).not.toBeInTheDocument()
    expect(screen.queryByText('engineering_plan')).not.toBeInTheDocument()
  })

  it('shows not available for null optional fields', () => {
    render(<PlannerDevPanel projection={sampleProjection} />)
    expect(screen.getAllByText('not available').length).toBeGreaterThan(0)
  })
})

describe('PlannerTraversalTimelineSection', () => {
  it('renders visited active blocked and skipped rows', () => {
    render(<PlannerTraversalTimelineSection projection={sampleProjection} />)
    expect(screen.getByText('Pipe Wall Thickness Workflow')).toBeInTheDocument()
    expect(screen.getByText('Straight Pipe Section')).toBeInTheDocument()
    expect(screen.getByText('Pressure Loading')).toBeInTheDocument()
    expect(screen.getByText('Waiting on: PARAM-straight-pipe-section')).toBeInTheDocument()
  })

  it('shows not available when timeline is empty', () => {
    render(
      <PlannerTraversalTimelineSection
        projection={{ ...sampleProjection, visited_timeline: [] }}
      />,
    )
    expect(screen.getByText('not available')).toBeInTheDocument()
  })
})

describe('TaskStateDevPanel', () => {
  it('shows structured task state panels without raw JSON in default view', () => {
    render(<TaskStateDevPanel payload={samplePayload} activeTaskState={null} />)
    expect(screen.getAllByText('Facts / inputs').length).toBeGreaterThan(0)
    expect(screen.getByText(/Developer \/ debug view only/)).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Raw State' })).not.toBeInTheDocument()
    expect(screen.getByText('Advanced / Raw Data — Canonical task state')).toBeInTheDocument()
  })
})
