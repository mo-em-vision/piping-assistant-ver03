import { describe, expect, it } from 'vitest'

import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

const legacyEq2Activation: DisplayOutputBlock = {
  id: 'node-activation-equation-B313-304.1.1-0',
  type: 'equation',
  title: 'eq-2',
  content: 't_m = t + c',
  display: 't_m = t + c',
  variables: [
    { symbol: 't', name: 'Required thickness' },
    { symbol: 'c', name: 'Corrosion allowance' },
  ],
}

const legacyEq2Preview: DisplayOutputBlock = {
  id: 'path-preview-equation-304.1.1-a',
  type: 'equation',
  content: 't_m = t + c',
  display: 't_m = t + c',
  input_table: {
    columns: [
      { key: 'symbol', label: 'Symbol', sortable: false },
      { key: 'definition', label: 'Definition', sortable: false },
      { key: 'value', label: 'Value', sortable: false },
    ],
    rows: [
      { symbol: 't', definition: 'Required thickness', value: 'Awaiting user input' },
      { symbol: 'c', definition: 'Corrosion allowance', value: 'Awaiting user input' },
    ],
  },
}

const stableEq2Block: DisplayOutputBlock = {
  id: 'equation-asme-b313-304-1-1-eq-2',
  type: 'equation',
  lifecycle: 'durable',
  display_role: 'equation',
  display_state: 'evaluated',
  equation_node_id: 'asme-b313-304-1-1-eq-2',
  source_node_id: '304.1.1-a',
  content: 't_m = t + c',
  display: 't_m = t + c',
  input_table: legacyEq2Preview.input_table,
}

const incomingEq3Block: DisplayOutputBlock = {
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
    columns: [
      { key: 'symbol', label: 'Symbol', sortable: false },
      { key: 'definition', label: 'Definition', sortable: false },
      { key: 'value', label: 'Value', sortable: false },
    ],
    rows: [{ symbol: 'P', definition: 'Design pressure', value: '8 bar' }],
  },
}

describe('mergeDisplayOutputs', () => {
  it('retains prior durable equation blocks when focus advances', () => {
    const merged = mergeDisplayOutputs([stableEq2Block], [incomingEq3Block])

    expect(merged.map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('preserves durable blocks while merging incoming focus equation', () => {
    const durableExplanation: DisplayOutputBlock = {
      id: 'preview-intro',
      type: 'text',
      lifecycle: 'durable',
      content: 'The minimum required wall thickness shall be computed.',
    }

    const merged = mergeDisplayOutputs(
      [stableEq2Block, durableExplanation],
      [incomingEq3Block, stableEq2Block],
    )

    expect(merged.map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'preview-intro',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('updates durable equation blocks in place by id', () => {
    const previous: DisplayOutputBlock = {
      ...stableEq2Block,
      display: 't_m = 2.000 + c',
    }
    const incoming: DisplayOutputBlock = {
      ...previous,
      display: 't_m = 2.252',
    }

    const merged = mergeDisplayOutputs([previous], [incoming])

    expect(merged).toHaveLength(1)
    if (merged[0]?.type === 'equation') {
      expect(merged[0].display).toBe('t_m = 2.252')
    }
  })

  it('drops volatile blocks from durable history', () => {
    const previous: DisplayOutputBlock = {
      id: 'planning-status',
      type: 'text',
      content: 'Awaiting input',
    }

    expect(mergeDisplayOutputs([previous], [])).toEqual([])
  })

  it('passes through ephemeral input_waiting from incoming snapshot only', () => {
    const waiting: DisplayOutputBlock = {
      id: 'input-waiting',
      type: 'text',
      content: 'Waiting for your input to continue the workflow.',
      display_role: 'input_waiting',
      lifecycle: 'volatile',
      volatile: true,
      history_eligible: false,
    }

    const merged = mergeDisplayOutputs([stableEq2Block], [waiting])
    expect(merged).toHaveLength(2)
    expect(merged[1]?.id).toBe('input-waiting')

    const afterSubmit = mergeDisplayOutputs(merged, [stableEq2Block])
    expect(afterSubmit.some((block) => block.id === 'input-waiting')).toBe(false)
  })

  it('retains stable preview equations when incoming snapshot omits them', () => {
    const previewEq2: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-1-eq-2',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-1-eq-2',
      source_node_id: '304.1.1-a',
      content: 't_m = t + c',
      display: 't_m = t + c',
      input_table: legacyEq2Preview.input_table,
    }

    const merged = mergeDisplayOutputs([previewEq2], [])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.id).toBe('equation-asme-b313-304-1-1-eq-2')
  })

  it('retains visited preview equation when focus advances to another equation', () => {
    const previewEq2: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-1-eq-2',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-1-eq-2',
      source_node_id: '304.1.1-a',
      content: 't_m = t + c',
      display: 't_m = t + c',
      input_table: legacyEq2Preview.input_table,
    }
    const previewEq3: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-2-eq-3a',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-2-eq-3a',
      source_node_id: '304.1.2-a',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
      input_table: incomingEq3Block.input_table,
    }

    const merged = mergeDisplayOutputs([previewEq2], [previewEq3])

    expect(merged.map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-1-eq-2',
      'equation-asme-b313-304-1-2-eq-3a',
    ])
  })

  it('drops legacy path-preview equations when incoming snapshot has no preview blocks', () => {
    const merged = mergeDisplayOutputs([legacyEq2Preview], [])

    expect(merged).toEqual([])
  })

  it('preserves durable blocks when incoming only contains volatile blocks', () => {
    const incoming: DisplayOutputBlock = {
      id: 'planning-status',
      type: 'text',
      content: 'Complete the fields below to continue.',
    }

    const merged = mergeDisplayOutputs([stableEq2Block, legacyEq2Preview], [incoming])

    expect(merged).toEqual([stableEq2Block])
  })

  it('replaces preview intro by display channel from incoming snapshot', () => {
    const previousIntro: DisplayOutputBlock = {
      id: 'path-preview-intro-304.1.1-a',
      type: 'text',
      content: 'Old intro',
    }
    const incomingIntro: DisplayOutputBlock = {
      id: 'path-preview-intro-304.1.2-a',
      type: 'text',
      lifecycle: 'preview',
      display_channel: 'current_node_intro',
      content: 'Minimum required wall thickness based on',
    }

    const merged = mergeDisplayOutputs([previousIntro], [incomingIntro, incomingEq3Block])

    expect(merged.map((block) => block.id)).toEqual([
      'equation-asme-b313-304-1-2-eq-3a',
      'path-preview-intro-304.1.2-a',
    ])
  })

  it('returns incoming durable blocks when previous is empty', () => {
    const incoming: DisplayOutputBlock[] = [
      {
        id: 'paragraph-304.1.1-a',
        type: 'text',
        lifecycle: 'durable',
        display_role: 'engineering_reference',
        content: 'Minimum required pipe wall thickness is 2.252 mm.',
      },
    ]

    expect(mergeDisplayOutputs([], incoming)).toEqual(incoming)
  })

  it('updates durable equation payload when incoming has newer input_table values', () => {
    const previousTrace: DisplayOutputBlock = {
      ...stableEq2Block,
      input_table: {
        columns: legacyEq2Preview.input_table!.columns,
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
    const incomingTrace: DisplayOutputBlock = {
      ...previousTrace,
      input_table: {
        columns: legacyEq2Preview.input_table!.columns,
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

    const merged = mergeDisplayOutputs([previousTrace], [incomingTrace])
    expect(merged).toHaveLength(1)
    const row = merged[0]?.type === 'equation' ? merged[0].input_table?.rows[0] : undefined
    expect(row?.value).toBe('2.000 mm')
  })

  it('updates durable equation when equation_display_trace payload changes', () => {
    const previousTrace: DisplayOutputBlock = {
      ...incomingEq3Block,
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-2-eq-3a',
        node_id: '304.1.2-a',
        symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
        substituted_latex: null,
        result_latex: null,
        latex_source: 'metadata_display_text',
        status: 'blocked',
        inputs: [],
        intermediate_values: [],
        result: null,
      },
    }
    const incomingTrace: DisplayOutputBlock = {
      ...previousTrace,
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-2-eq-3a',
        node_id: '304.1.2-a',
        symbolic_latex: 't = \\frac{PD}{2(SEW + PY)}',
        substituted_latex: 't = \\frac{(1)(2)}{2((3)(4)(5) + (1)(6))} = 7\\ \\mathrm{mm}',
        result_latex: '7\\ \\mathrm{mm}',
        latex_source: 'metadata_display_text',
        status: 'evaluated',
        inputs: [],
        intermediate_values: [],
        result: {
          symbol: 't',
          value: 7,
          unit: 'mm',
          display_value: '7\\ \\mathrm{mm}',
        },
      },
      content: 't = \\frac{(1)(2)}{2((3)(4)(5) + (1)(6))} = 7\\ \\mathrm{mm}',
    }

    const merged = mergeDisplayOutputs([previousTrace], [incomingTrace])
    expect(merged).toHaveLength(1)
    if (merged[0]?.type === 'equation') {
      expect(merged[0].equation_display_trace?.status).toBe('evaluated')
      expect(merged[0].equation_display_trace?.substituted_latex).toContain('7')
    }
  })

  it('does not replace durable equations by display_channel', () => {
    const merged = mergeDisplayOutputs(
      [legacyEq2Activation, legacyEq2Preview],
      [incomingEq3Block],
    )

    expect(merged.map((block) => block.id)).toEqual(['equation-asme-b313-304-1-2-eq-3a'])
  })

  it('includes incoming preview equation blocks with stable ids', () => {
    const previewEq3: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-2-eq-3a',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-2-eq-3a',
      source_node_id: '304.1.2-a',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
      input_table: incomingEq3Block.input_table,
    }

    const merged = mergeDisplayOutputs([], [previewEq3])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.id).toBe('equation-asme-b313-304-1-2-eq-3a')
    if (merged[0]?.type === 'equation') {
      expect(merged[0].display_state).toBe('preview')
    }
  })

  it('prefers richer preview equation when incoming has partial substitution', () => {
    const previewEq2: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-1-eq-2',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-1-eq-2',
      content: 't_m = t + c',
      display: 't_m = t + c',
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-1-eq-2',
        status: 'blocked',
        symbolic_latex: 't_m = t + c',
        substituted_latex: null,
        result_latex: null,
        inputs: [],
        intermediate_values: [],
        result: null,
      },
    }
    const richerEq2: DisplayOutputBlock = {
      ...previewEq2,
      equation_display_trace: {
        equation_id: 'asme-b313-304-1-1-eq-2',
        status: 'blocked',
        symbolic_latex: 't_m = t + c',
        substituted_latex: 't_m = (2\\ \\mathrm{mm}) + c',
        result_latex: null,
        inputs: [],
        intermediate_values: [],
        result: null,
      },
      equation_content: 'substituted',
    }

    const merged = mergeDisplayOutputs([previewEq2], [richerEq2])

    expect(merged).toHaveLength(1)
    if (merged[0]?.type === 'equation') {
      expect(merged[0].equation_display_trace?.substituted_latex).toContain('2')
    }
  })

  it('replaces preview equation with durable evaluated block for same stable id', () => {
    const previewEq3: DisplayOutputBlock = {
      id: 'equation-asme-b313-304-1-2-eq-3a',
      type: 'equation',
      lifecycle: 'preview',
      display_role: 'equation',
      display_state: 'preview',
      equation_node_id: 'asme-b313-304-1-2-eq-3a',
      content: 't = PD / 2(SEW + PY)',
      display: 't = PD / 2(SEW + PY)',
    }

    const merged = mergeDisplayOutputs([previewEq3], [incomingEq3Block])

    expect(merged).toHaveLength(1)
    expect(merged[0]?.id).toBe('equation-asme-b313-304-1-2-eq-3a')
    if (merged[0]?.type === 'equation') {
      expect(merged[0].display_state).toBe('evaluated')
    }
  })
})
