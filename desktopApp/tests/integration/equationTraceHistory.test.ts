import { describe, expect, it } from 'vitest'

import { buildWorkflowHistory } from '@/components/workflow/buildWorkflowHistory'
import { withPreservedDisplayOutputs } from '@/store/taskStore'
import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

const eq2Preview: DisplayOutputBlock = {
  id: 'path-preview-equation-304.1.1-a',
  type: 'equation',
  lifecycle: 'preview',
  display_role: 'preview',
  display_channel: 'current_equation_preview',
  equation_node_id: 'asme-b313-304-1-1-eq-2',
  source_node_id: '304.1.1-a',
  content: 't_m = t + c',
  display: 't_m = t + c',
  input_table: {
    columns: [
      { key: 'symbol', label: 'Symbol', sortable: false },
      { key: 'definition', label: 'Definition', sortable: false },
      { key: 'value', label: 'Value', sortable: false },
    ],
    rows: [
      {
        symbol: 't',
        definition: 'Required thickness',
        value: '',
        value_reference: { node_id: '304.1.2-a', label: '§304.1.2' },
      },
    ],
  },
}

const eq2Trace: DisplayOutputBlock = {
  id: 'equation-trace-304.1.1-a-asme-b313-304-1-1-eq-2',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'equation_trace',
  equation_node_id: 'asme-b313-304-1-1-eq-2',
  source_node_id: '304.1.1-a',
  content: 't_m = t + c',
  display: 't_m = t + c',
  input_table: eq2Preview.input_table,
}

const eq3Preview: DisplayOutputBlock = {
  id: 'path-preview-equation-304.1.2-a',
  type: 'equation',
  lifecycle: 'preview',
  display_role: 'preview',
  display_channel: 'current_equation_preview',
  equation_node_id: 'asme-b313-304-1-2-eq-3a',
  source_node_id: '304.1.2-a',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
  input_table: {
    columns: eq2Preview.input_table!.columns,
    rows: [{ symbol: 'P', definition: 'Design pressure', value: '8 bar' }],
  },
}

function baseState(display_outputs: DisplayOutputBlock[]): TaskStateDto {
  return {
    task_id: 'task-1',
    name: 'Pipe Wall',
    description: '',
    discipline: 'piping',
    workflow_id: 'pipe_wall_thickness_design',
    status: 'awaiting_input',
    display_outputs,
  } as TaskStateDto
}

describe('equation trace history sequence', () => {
  it('shows eq-2 once at workflow start and caches durable trace only', () => {
    const incoming = baseState([eq2Preview, eq2Trace])
    const merged = withPreservedDisplayOutputs(null, incoming)
    const history = buildWorkflowHistory([], merged.display_outputs ?? [], merged.workflow_id)

    expect(history.map((item) => item.block.id)).toEqual(['path-preview-equation-304.1.1-a'])
  })

  it('keeps eq-2 trace when preview moves to eq-3a', () => {
    const afterStart = withPreservedDisplayOutputs(null, baseState([eq2Preview, eq2Trace]))
    const afterBranch = withPreservedDisplayOutputs(
      afterStart,
      baseState([eq2Trace, eq3Preview]),
    )
    const history = buildWorkflowHistory([], afterBranch.display_outputs ?? [], afterBranch.workflow_id)

    expect(history.map((item) => item.block.id)).toEqual([
      'equation-trace-304.1.1-a-asme-b313-304-1-1-eq-2',
      'path-preview-equation-304.1.2-a',
    ])
  })

  it('updates eq-2 trace values without duplicating on refresh', () => {
    const staleTrace: DisplayOutputBlock = {
      ...eq2Trace,
      input_table: {
        columns: eq2Trace.input_table!.columns,
        rows: [
          {
            symbol: 't',
            definition: 'Required thickness',
            value: '',
            value_reference: { node_id: '304.1.2-a', label: '§304.1.2' },
          },
        ],
      },
    }
    const updatedTrace: DisplayOutputBlock = {
      ...eq2Trace,
      input_table: {
        columns: eq2Trace.input_table!.columns,
        rows: [
          {
            symbol: 't',
            definition: 'Required thickness',
            value: '2.000 mm',
            value_reference: { node_id: '304.1.2-a', label: '§304.1.2' },
            value_status: 'equation_derived',
          },
        ],
      },
    }

    const afterBranch = withPreservedDisplayOutputs(
      null,
      baseState([staleTrace, eq3Preview]),
    )
    const refreshed = withPreservedDisplayOutputs(
      afterBranch,
      baseState([updatedTrace, eq3Preview]),
    )

    const traces = (refreshed.display_outputs ?? []).filter(
      (block) => block.display_role === 'equation_trace',
    )
    expect(traces).toHaveLength(1)
    const row = traces[0]?.type === 'equation' ? traces[0].input_table?.rows[0] : undefined
    expect(row?.value).toBe('2.000 mm')
  })
})
