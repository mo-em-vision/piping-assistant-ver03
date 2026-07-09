import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { PlannerDevPanel } from '@dev-ui/inspector/PlannerDevPanel'
import { TaskStateDevPanel } from '@dev-ui/inspector/TaskStateDevPanel'

import type { InspectionPayloadDto, PlannerDebugViewDto } from '@/types/backend/inspection'

const openReferenceTab = vi.fn()

vi.mock('@/store/rightPanelStore', () => ({
  useRightPanelStore: (selector: (state: { openReferenceTab: typeof openReferenceTab }) => unknown) =>
    selector({ openReferenceTab }),
}))

const sampleProjection: PlannerDebugViewDto = {
  current_node: {
    node_id: 'NODE-sample',
    node_type: 'parameter',
    display_name: 'Sample Input',
  },
  next_queued_node: {
    node_id: 'NODE-pending',
    node_type: 'paragraph',
    display_name: 'Pending Paragraph',
  },
  goals: {
    main_goal: 'Generic Sample Calculation',
    subgoals: ['Sample Output', 'Sample Report'],
  },
  groups: {
    visited_previous_step: [
      {
        node_id: 'WF-GENERIC',
        node_type: 'workflow',
        display_name: 'Generic Workflow',
      },
    ],
    queue_leaf_nodes: [
      {
        node_id: 'NODE-pending',
        node_type: 'paragraph',
        display_name: 'Pending Paragraph',
        status_reason: 'waiting for dependency',
      },
    ],
    visited_from_beginning: [
      {
        node_id: 'WF-GENERIC',
        node_type: 'workflow',
        display_name: 'Generic Workflow',
      },
    ],
    excluded_blocked: [
      {
        node_id: 'NODE-excluded',
        node_type: 'paragraph',
        display_name: 'Excluded Paragraph',
      },
    ],
  },
}

const samplePayload: InspectionPayloadDto = {
  task_id: 'task-1',
  workflow_id: 'generic-sample',
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
      workflow_id: 'generic_sample_workflow',
      selected_root: 'generic_sample_workflow',
      current_phase: 'parameter_gathering',
      readiness: 'waiting_for_input',
      expanded_node_count: 1,
      missing_input_count: 1,
    },
    facts_view: [
      {
        field: 'sample_input',
        label: 'Sample Input',
        symbol: 'sample_input',
        value: null,
        unit: null,
        source: 'user_input',
        status: 'missing',
        parameter_node_id: 'PARAM-sample-input',
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
        node_id: 'NODE-sample',
        message: 'Field: sample_input',
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
  it('renders minimal debugger view without JSON', () => {
    render(<PlannerDevPanel projection={sampleProjection} />)

    expect(screen.getByText(/Current node:/)).toBeInTheDocument()
    expect(screen.getByText(/\[parameter\] Sample Input/)).toBeInTheDocument()
    expect(screen.getByText(/Next queued node:/)).toBeInTheDocument()
    expect(screen.getByText(/\[paragraph\] Pending Paragraph/)).toBeInTheDocument()
    expect(screen.getByText('Goal')).toBeInTheDocument()
    expect(screen.getByText('Generic Sample Calculation')).toBeInTheDocument()
    expect(screen.getByText('Sample Output')).toBeInTheDocument()
    expect(screen.getByText('Visited in previous step (1)')).toBeInTheDocument()
    expect(screen.getByText('Queue / leaf nodes awaiting expansion (1)')).toBeInTheDocument()
    expect(screen.getByText(/\[paragraph\] Pending Paragraph — waiting for dependency/)).toBeInTheDocument()
    expect(screen.getByText('Visited from beginning (1)')).toBeInTheDocument()
    expect(screen.getByText('Excluded / blocked (1)')).toBeInTheDocument()
    expect(screen.queryByText('engineering_plan')).not.toBeInTheDocument()
    expect(screen.queryByText('PLAN-test')).not.toBeInTheDocument()
    expect(screen.queryByText('Pipe Wall')).not.toBeInTheDocument()
  })

  it('opens reference tab when a node row is clicked', async () => {
    const user = userEvent.setup()
    render(<PlannerDevPanel projection={sampleProjection} />)

    await user.click(screen.getByRole('button', { name: '[workflow] Generic Workflow' }))
    expect(openReferenceTab).toHaveBeenCalledWith('WF-GENERIC', 'Generic Workflow')
  })

  it('shows none for missing current and next nodes', () => {
    render(
      <PlannerDevPanel
        projection={{
          ...sampleProjection,
          current_node: null,
          next_queued_node: null,
        }}
      />,
    )

    expect(screen.getByText(/Current node:\s*none/)).toBeInTheDocument()
    expect(screen.getByText(/Next queued node:\s*none/)).toBeInTheDocument()
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
