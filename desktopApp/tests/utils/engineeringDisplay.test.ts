import { describe, expect, it } from 'vitest'

import { buildTaskStateViewModel } from '@/store/taskStateManager'
import { formatEngineeringDisplayValue } from '@/utils/engineeringDisplay'

describe('engineeringDisplay', () => {
  it('converts pascal stress values to MPa', () => {
    expect(formatEngineeringDisplayValue(193_000_000, 'Pa')).toBe('193 MPa')
    expect(formatEngineeringDisplayValue(8, 'bar')).toBe('8 bar')
  })
})

describe('taskStateManager stress display', () => {
  it('formats timeline fallback values in MPa when unit is Pa', () => {
    const viewModel = buildTaskStateViewModel({
      task_id: 'task-1',
      name: 'Pipe Thickness Calculation',
      workflow_id: 'pipe_wall_thickness_design',
      discipline: 'Piping',
      description: '',
      status: 'awaiting_input',
      active_nodes: [],
      progress: {
        timeline: [
          {
            id: 'allowable_stress',
            title: 'Allowable stress (S)',
            status: 'done',
            value: 193_000_000,
            unit: 'Pa',
          },
        ],
        steps: [],
        missing_inputs: [],
        missing_assumptions: [],
        step_progress: [],
      },
      inputs: {},
      outputs: {},
      warnings: [],
      parameters: [],
      display_outputs: [],
      options: { available_workflows: [] },
      errors: [],
    })

    expect(viewModel?.timeline[0]?.displayValue).toBe('193 MPa')
  })
})
