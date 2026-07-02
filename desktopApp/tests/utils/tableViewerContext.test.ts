import { describe, expect, it } from 'vitest'

import { buildTableViewerContext } from '@/utils/tableViewerContext'
import type { TaskStateDto } from '@/types/backend/api'

function buildTaskState(facts: Record<string, unknown>): TaskStateDto {
  return {
    task_id: 'task-1',
    name: 'Demo task',
    workflow_id: 'pipe-wall-thickness',
    discipline: 'Piping',
    description: 'Demo',
    status: 'in_progress',
    active_nodes: [],
    progress: {
      timeline: [],
      steps: [],
      missing_inputs: [],
      missing_assumptions: [],
      step_progress: [],
    },
    facts,
    outputs: {},
    warnings: [],
    parameters: [],
    display_outputs: [],
    options: {},
    errors: [],
  }
}

describe('buildTableViewerContext', () => {
  it('highlights design temperature for Table 304.1.1 without material filters', () => {
    const context = buildTableViewerContext(
      'asme_b31.3_table_304_1_1',
      buildTaskState({
        material: { value: 'carbon_steel', display_value: 'Carbon Steel' },
        design_temperature: { value: 350, display_value: '350 °F' },
      }),
    )

    expect(context?.columnFilters).toBeUndefined()
    expect(context?.highlightKeys?.design_temperature).toBe('350 °F')
    expect(context?.highlightKeys?.material).toBe('Carbon Steel')
  })

  it('returns undefined when task state has no relevant inputs', () => {
    const context = buildTableViewerContext('table_304_1_1', buildTaskState({}))
    expect(context).toBeUndefined()
  })
})
