import { describe, expect, it } from 'vitest'

import { buildCenterPanelTranscript } from '@/utils/buildCenterPanelTranscript'
import {
  assertUserVisibleText,
  guidanceTranscriptToDisplayBlocks,
} from '@/utils/flowGuidanceTranscript'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

describe('guidanceTranscriptToDisplayBlocks', () => {
  it('converts runtime workflow intro blocks to durable text display blocks', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'workflow-intro-pipe_wall_thickness_design',
        kind: 'text',
        source: 'runtime',
        text: 'Pipe Wall Thickness Design\n\nDetermine minimum required pipe wall thickness.',
        payload: { display_role: 'workflow_intro', title: 'Pipe Wall Thickness Design' },
      },
    ])

    expect(blocks).toHaveLength(1)
    expect(blocks[0]?.display_role).toBe('workflow_intro')
    expect(blocks[0]?.title).toBe('Pipe Wall Thickness Design')
  })

  it('includes workflow intro first and appends guidance after engineering blocks', () => {
    const displayOutputs: DisplayOutputBlock[] = [
      {
        id: 'equation-asme-b313-304-1-2-eq-3a',
        type: 'equation',
        content: 't = PD / 2(SEW + PY)',
        display_role: 'equation',
        display_state: 'evaluated',
        lifecycle: 'durable',
      },
    ]
    const transcript = [
      {
        block_id: 'guidance-pipe_wall_thickness_design-pressure-loading-branch',
        kind: 'guidance',
        source: 'guidance',
        text: 'Branch narration text.',
        payload: { display_role: 'branch_narration' },
      },
      {
        block_id: 'workflow-intro-pipe_wall_thickness_design',
        kind: 'text',
        source: 'runtime',
        text: 'Determine minimum required pipe wall thickness from applicable standards.',
        payload: { display_role: 'workflow_intro' },
      },
    ]

    const items = buildCenterPanelTranscript(displayOutputs, transcript, 'pipe_wall_thickness_design')
    expect(items).toHaveLength(3)
    expect(items[0]?.block.id).toBe('workflow-intro-pipe_wall_thickness_design')
    expect(items[1]?.block.id).toContain('guidance-')
    expect(items[2]?.block.id).toBe('equation-asme-b313-304-1-2-eq-3a')
  })

  it('rejects internal leak text in merged transcript output', () => {
    const leaked = '{"GOAL-1": "internal"}'
    expect(assertUserVisibleText(leaked)).toBe(false)
    const merged = buildCenterPanelTranscript(
      [{ id: 'paragraph-304.1.1-a', type: 'text', content: 'Visible summary.', display_role: 'paragraph_context', lifecycle: 'durable' }],
      [],
    )
    const visible = merged.map((item) => item.block.content ?? '').join(' ')
    expect(assertUserVisibleText(visible)).toBe(true)
  })

  it('converts guidance transcript blocks to durable text display blocks', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Before collecting design parameters, the workflow confirms gate context.',
        payload: { display_role: 'branch_narration' },
      },
      {
        block_id: 'prompt-abc',
        kind: 'prompt',
        source: 'messaging',
        text: 'Should not render in transcript merge',
      },
    ])

    expect(blocks).toHaveLength(1)
    expect(blocks[0]?.id).toBe('guidance-pipe_wall_thickness_design-expansion-gate-intro')
    expect(blocks[0]?.display_role).toBe('branch_narration')
    expect(blocks[0]?.lifecycle).toBe('durable')
  })

  it('excludes input archive blocks from guidance transcript conversion', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'archived-ask-straight_pipe_section-1',
        kind: 'ask_archive',
        source: 'input_archive',
        text: 'Is this a straight pipe section?',
      },
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Branch narration only.',
      },
    ])

    expect(blocks).toHaveLength(1)
    expect(blocks[0]?.id).toBe('guidance-pipe_wall_thickness_design-expansion-gate-intro')
  })
})

describe('buildCenterPanelTranscript', () => {
  it('orders next_workflows after result summary in center panel merge', () => {
    const displayOutputs: DisplayOutputBlock[] = []
    const transcript = [
      {
        block_id: 'result-summary-pipe_wall_thickness_design',
        kind: 'text',
        source: 'runtime',
        text: 'Calculation complete.',
        payload: { display_role: 'result_summary' },
      },
      {
        block_id: 'next-workflows-task-1-pipe_wall_thickness_design',
        kind: 'next_workflows',
        source: 'workflow_runtime',
        title: 'Suggested next workflows',
        text: 'Based on this workflow, you may continue with:',
        suggestions: [
          {
            workflow_id: 'mawp_design',
            title: 'MAWP Design',
            available: true,
            action: { type: 'start_workflow', workflow_id: 'mawp_design' },
          },
        ],
      },
    ]

    const items = buildCenterPanelTranscript(displayOutputs, transcript, 'pipe_wall_thickness_design')
    expect(items.at(-1)?.block.id).toBe('next-workflows-task-1-pipe_wall_thickness_design')
    expect(items.at(-1)?.block.display_role).toBe('next_workflows')
  })

  it('converts next_workflows transcript blocks for scroll rendering', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'next-workflows-task-1-pipe_wall_thickness_design',
        kind: 'next_workflows',
        source: 'workflow_runtime',
        title: 'Suggested next workflows',
        text: 'Based on this workflow, you may continue with:',
        suggestions: [
          {
            workflow_id: 'mawp_design',
            title: 'MAWP Design',
            description: 'Calculate MAWP from thickness.',
            available: false,
          },
        ],
      },
    ])

    expect(blocks).toHaveLength(1)
    expect(blocks[0]?.type).toBe('next_workflows')
    if (blocks[0]?.type === 'next_workflows') {
      expect(blocks[0].suggestions[0]?.title).toBe('MAWP Design')
      expect(blocks[0].suggestions[0]?.action).toBeUndefined()
    }
  })

  it('merges transcript guidance with display outputs without duplicate ids', () => {
    const displayOutputs: DisplayOutputBlock[] = [
      {
        id: 'equation-trace-1',
        type: 'equation',
        content: 't = 1',
        display: 't = 1',
        display_role: 'equation',
        display_state: 'evaluated',
      },
    ]
    const transcript = [
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Branch narration text.',
        payload: { display_role: 'branch_narration' },
      },
    ]

    const items = buildCenterPanelTranscript(displayOutputs, transcript, 'pipe_wall_thickness_design')

    expect(items).toHaveLength(2)
    const ids = items.map((item) => item.block.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids[0]).toContain('guidance-')
    expect(ids[1]).toBe('equation-trace-1')
  })

  it('does not duplicate guidance when transcript already contains the block', () => {
    const transcript = [
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Branch narration text.',
      },
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Duplicate should be ignored by backend; frontend still dedupes.',
      },
    ]

    const items = buildCenterPanelTranscript([], transcript)
    const guidanceItems = items.filter((item) => item.block.id.startsWith('guidance-'))
    expect(guidanceItems).toHaveLength(1)
  })

  it('orders branch narration before evaluated equation blocks', () => {
    const displayOutputs: DisplayOutputBlock[] = [
      {
        id: 'equation-trace-1',
        type: 'equation',
        content: 't = 1',
        display: 't = 1',
        display_role: 'equation',
        display_state: 'evaluated',
      },
    ]
    const transcript = [
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Branch narration text.',
        payload: { display_role: 'branch_narration' },
      },
    ]

    const items = buildCenterPanelTranscript(displayOutputs, transcript)
    expect(items[0]?.block.id).toContain('guidance-')
    expect(items[1]?.block.id).toBe('equation-trace-1')
  })
})

describe('assertUserVisibleText', () => {
  it('flags internal planner json markers', () => {
    expect(assertUserVisibleText('Normal engineering narration.')).toBe(true)
    expect(assertUserVisibleText('{"GOAL-1": "blocked"}')).toBe(false)
    expect(assertUserVisibleText('waiting_user_input')).toBe(false)
  })
})
