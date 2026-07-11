import { describe, expect, it } from 'vitest'

import { buildCenterPanelTranscript } from '@/utils/buildCenterPanelTranscript'
import { buildWorkflowHistory } from '@/components/workflow/buildWorkflowHistory'
import { withPreservedDisplayOutputs } from '@/store/taskStore'
import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

const eq2Block: DisplayOutputBlock = {
  id: 'equation-asme-b313-304-1-1-eq-2',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'equation',
  display_state: 'evaluated',
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

const eq3Block: DisplayOutputBlock = {
  id: 'equation-asme-b313-304-1-2-eq-3a',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'equation',
  display_state: 'evaluated',
  equation_node_id: 'asme-b313-304-1-2-eq-3a',
  source_node_id: '304.1.2-a',
  content: 't = PD / 2(SEW + PY)',
  display: 't = PD / 2(SEW + PY)',
  input_table: {
    columns: eq2Block.input_table!.columns,
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

function isEvaluatedEquationBlock(block: DisplayOutputBlock): boolean {
  return block.display_role === 'equation' && block.display_state === 'evaluated'
}

describe('equation trace history sequence', () => {
  it('shows durable equation block when equation is not yet evaluated', () => {
    const incoming = baseState([eq2Block])
    const merged = withPreservedDisplayOutputs(null, incoming)
    const history = buildWorkflowHistory([], merged.display_outputs ?? [], merged.workflow_id)

    expect(history.map((item) => item.block.id)).toEqual(['equation-asme-b313-304-1-1-eq-2'])
  })

  it('keeps eq-2 block when focus advances to eq-3a', () => {
    const afterStart = withPreservedDisplayOutputs(null, baseState([eq2Block]))
    const afterBranch = withPreservedDisplayOutputs(afterStart, baseState([eq2Block, eq3Block]))
    const history = buildWorkflowHistory([], afterBranch.display_outputs ?? [], afterBranch.workflow_id)

    expect(history.map((item) => item.block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('shows both evaluated equations without duplicate ids', () => {
    const evaluatedEq2: DisplayOutputBlock = {
      ...eq2Block,
      display: 't_m = 2.252',
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-1-eq-2',
        node_id: '304.1.1-a',
        symbolic_latex: 't_m = t + c',
        substituted_latex: 't_m = 2.252\\ \\mathrm{mm}',
        result_latex: '2.252\\ \\mathrm{mm}',
        latex_source: 'metadata_display_text',
        status: 'evaluated',
        inputs: [],
        intermediate_values: [],
        result: { symbol: 't_m', value: 2.252, unit: 'mm', display_value: '2.252\\ \\mathrm{mm}' },
      },
    }
    const evaluatedEq3: DisplayOutputBlock = {
      ...eq3Block,
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-2-eq-3a',
        node_id: '304.1.2-a',
        symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
        substituted_latex: 't = 2.252\\ \\mathrm{mm}',
        result_latex: '2.252\\ \\mathrm{mm}',
        latex_source: 'metadata_display_text',
        status: 'evaluated',
        inputs: [],
        intermediate_values: [],
        result: { symbol: 't', value: 2.252, unit: 'mm', display_value: '2.252\\ \\mathrm{mm}' },
      },
    }

    const afterEval = withPreservedDisplayOutputs(null, baseState([evaluatedEq2, evaluatedEq3]))
    const history = buildWorkflowHistory([], afterEval.display_outputs ?? [], afterEval.workflow_id)
    const ids = history.map((item) => item.block.id)

    expect(ids).toContain('equation-asme-b313-304-1-2-eq-3a')
    expect(ids).toContain('equation-asme-b313-304-1-1-eq-2')
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('updates eq-2 trace values without duplicating on refresh', () => {
    const staleTrace: DisplayOutputBlock = {
      ...eq2Block,
      input_table: {
        columns: eq2Block.input_table!.columns,
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
      ...eq2Block,
      input_table: {
        columns: eq2Block.input_table!.columns,
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

    const afterBranch = withPreservedDisplayOutputs(null, baseState([staleTrace, eq3Block]))
    const refreshed = withPreservedDisplayOutputs(afterBranch, baseState([updatedTrace, eq3Block]))

    const traces = (refreshed.display_outputs ?? []).filter(
      (block) =>
        isEvaluatedEquationBlock(block) && block.equation_node_id === 'asme-b313-304-1-1-eq-2',
    )
    expect(traces).toHaveLength(1)
    const row = traces[0]?.type === 'equation' ? traces[0].input_table?.rows[0] : undefined
    expect(row?.value).toBe('2.000 mm')
  })

  it('orders evaluated equation blocks by stable id in center panel merge', () => {
    const items = buildCenterPanelTranscript([eq2Block, eq3Block], [], 'pipe_wall_thickness_design')
    const ids = items.map((item) => item.block.id)
    expect(ids.indexOf('equation-asme-b313-304-1-1-eq-2')).toBeLessThan(
      ids.indexOf('equation-asme-b313-304-1-2-eq-3a'),
    )
  })
})
