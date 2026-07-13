import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlannerDevPanel } from '@dev-ui/inspector/PlannerDevPanel'
import { TaskStateDevPanel } from '@dev-ui/inspector/TaskStateDevPanel'
import {
  assertNormalInspectorTableCells,
  assertPlannerDebugRowsExcludeRawJson,
  assertRawJsonLimitedToAdvancedSections,
} from '../helpers/inspectorTableContract'
import type { InspectionPayloadDto, PlannerDebugViewDto } from '@/types/backend/inspection'

const plannerProjectionFixture: PlannerDebugViewDto = {
  current_node: {
    node_id: 'PARAM-corrosion-allowance',
    node_type: 'parameter',
    display_name: 'PARAM-corrosion-allowance',
    label: 'Corrosion allowance',
  },
  next_queued_node: {
    node_id: 'asme-b313-304-1-2-eq-3a',
    node_type: 'equation',
    display_name: 'asme-b313-304-1-2-eq-3a',
    label: 'Internal Pressure Wall Thickness — Eq. (3a)',
  },
  goals: {
    main_goal: 'Pipe Wall Thickness Design',
    subgoals: ['Required wall thickness', 'Minimum required thickness'],
  },
  groups: {
    visited_previous_step: [
      {
        node_id: '304.1.2-a',
        node_type: 'paragraph',
        display_name: '304.1.2-a',
        label: 'Straight pipe under internal pressure',
        status_reason: 'ready_for_expansion',
      },
    ],
    queue_leaf_nodes: [
      {
        node_id: 'PARAM-corrosion-allowance',
        node_type: 'parameter',
        display_name: 'PARAM-corrosion-allowance',
        label: 'Corrosion allowance',
        status_reason: 'waiting_for_user_input',
      },
    ],
    visited_from_beginning: [
      {
        node_id: 'pipe_wall_thickness_design',
        node_type: 'workflow',
        display_name: 'pipe_wall_thickness_design',
        label: 'Pipe Wall Thickness Design',
      },
      {
        node_id: '304.1.1-a',
        node_type: 'paragraph',
        display_name: '304.1.1-a',
        label: 'Design thickness and allowances',
      },
    ],
    excluded_nodes: [],
    blocked_nodes: [],
    excluded_blocked: [],
  },
}

const inspectionPayloadFixture: InspectionPayloadDto = {
  task_id: 'pipe-wall-thickness-desi-fixture',
  workflow_id: 'pipe_wall_thickness_design',
  execution_trace: [],
  planner_decisions: {},
  planning_summary: {},
  provenance_index: [],
  provenance_warnings: [],
  workflow_state: {},
  execution_events: [],
  lifecycle_events: [],
  replay_frames: [],
  replay_snapshot: {},
  integrity_checks: [],
  performance: { total_duration_ms: 0, step_count: 0, by_node_ms: {} },
  breakpoint: {},
  canonical_task_state: {
    engineering_plan: {
      requirements: {
        'REQ-material_grade': { field: 'material_grade', status: 'resolved' },
      },
    },
  },
  task_state_views: {
    state_summary: {
      task_id: 'pipe-wall-thickness-desi-fixture',
      task_name: 'Pipe Wall Thickness Design',
      status: 'completed',
      workflow_id: 'pipe_wall_thickness_design',
      selected_root: 'pipe_wall_thickness_design',
      current_phase: 'ready',
      readiness: 'ready',
      expanded_node_count: 8,
      missing_input_count: 0,
    },
    facts_view: [
      {
        field: 'internal_design_gage_pressure',
        label: 'Internal design gage pressure',
        symbol: 'P',
        value: '8 bar',
        unit: 'bar',
        source: 'user_input',
        status: 'confirmed',
      },
      {
        field: 'material_grade',
        label: 'Material grade',
        value: 'astm_a106_gr_b',
        unit: 'dimensionless',
        source: 'user_input',
        status: 'confirmed',
      },
      {
        field: 'design_temperature',
        label: 'Design temperature',
        value: '38.0 degC',
        unit: 'C',
        source: 'user_input',
        status: 'confirmed',
      },
      {
        field: 'outside_diameter',
        label: 'Outside diameter',
        symbol: 'D',
        value: '168.3 mm',
        unit: 'mm',
        source: 'table_lookup',
        status: 'confirmed',
      },
      {
        field: 'allowable_stress',
        label: 'Allowable stress',
        symbol: 'S',
        value: '206.944 MPa',
        unit: 'MPa',
        source: 'table_lookup',
        status: 'confirmed',
      },
      {
        field: 'basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes',
        label: 'Joint efficiency',
        symbol: 'E_j',
        value: '1.0',
        unit: 'dimensionless',
        source: 'table_lookup',
        status: 'confirmed',
      },
    ],
    decisions_view: [
      {
        kind: 'assumption',
        field: 'straight_pipe_section',
        value: true,
        source: 'user_input',
        selected_node: '304.1.2-a',
      },
      {
        kind: 'path_decision',
        field: 'pressure_loading',
        value: 'internal_pressure',
        source: 'user_input',
        selected_node: '304.1.2-a',
      },
    ],
    outputs_view: [
      {
        field: 'required_thickness',
        label: 'Required wall thickness',
        value: '0.325 mm',
        unit: 'mm',
        producing_node: 'asme-b313-304-1-2-eq-3a',
        status: 'confirmed',
        warnings: [],
      },
      {
        field: 'minimum_required_thickness',
        label: 'Minimum required thickness',
        value: '0.325 mm',
        unit: 'mm',
        producing_node: 'asme-b313-304-1-1-eq-2',
        status: 'confirmed',
        warnings: [],
      },
    ],
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
        node_id: 'PARAM-nominal-pipe-size',
        message: 'Nominal pipe size requested',
        timestamp: '2026-07-13T00:00:00Z',
        source: 'execution',
      },
      {
        order: 2,
        event_type: 'table_lookup',
        label: 'Allowable stress resolved',
        node_id: 'asme-b313-table-A-1',
        message: 'Resolved from Table A-1',
        timestamp: '2026-07-13T00:00:05Z',
        source: 'execution',
      },
    ],
  },
  planner_debug_projection: plannerProjectionFixture,
}

describe('plannerDevPanelRegression', () => {
  it('PlannerDevPanel list rows stay free of raw planner JSON', () => {
    const { container } = render(<PlannerDevPanel projection={plannerProjectionFixture} />)

    expect(screen.getByText(/Current node:/)).toBeInTheDocument()
    expect(screen.getAllByText(/PARAM-corrosion-allowance/).length).toBeGreaterThan(0)
    assertPlannerDebugRowsExcludeRawJson(container)
    expect(container.querySelector('table.inspector-table')).toBeNull()
  })

  it('TaskStateDevPanel normal table rows stay free of large raw JSON', () => {
    const { container } = render(
      <TaskStateDevPanel payload={inspectionPayloadFixture} activeTaskState={null} />,
    )

    expect(screen.getByText('Internal design gage pressure')).toBeInTheDocument()
    expect(screen.getByText('Allowable stress')).toBeInTheDocument()
    assertNormalInspectorTableCells(container)
  })

  it('TaskStateDevPanel keeps engineering_plan JSON in advanced sections only', () => {
    const { container } = render(
      <TaskStateDevPanel payload={inspectionPayloadFixture} activeTaskState={null} />,
    )

    assertRawJsonLimitedToAdvancedSections(container)
    expect(screen.getByText('Advanced / Raw Data — Canonical task state')).toBeInTheDocument()
    const advancedBlocks = container.querySelectorAll('.inspector-advanced pre.inspector-code')
    expect(advancedBlocks[0]?.textContent ?? '').toContain('engineering_plan')
    assertNormalInspectorTableCells(container)
  })
})
