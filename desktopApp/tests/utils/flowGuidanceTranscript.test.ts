import { describe, expect, it } from 'vitest'

import { buildCenterPanelTranscript } from '@/utils/buildCenterPanelTranscript'
import { guidanceTranscriptToDisplayBlocks } from '@/utils/flowGuidanceTranscript'

describe('input archive transcript rendering', () => {
  it('does not convert ask_archive or answer_archive blocks for center scroll', () => {
    const transcript = [
      {
        block_id: 'archived-ask-straight_pipe_section-FACT-001',
        kind: 'ask_archive',
        source: 'input_archive',
        text: 'Is the pipe wall thickness you would like to calculate for a straight section of pipe?',
        payload: { display_role: 'ask_archive', parameter_id: 'straight_pipe_section' },
      },
      {
        block_id: 'archived-answer-straight_pipe_section-FACT-001',
        kind: 'answer_archive',
        source: 'input_archive',
        text: 'Yes',
        payload: {
          display_role: 'answer_archive',
          parameter_id: 'straight_pipe_section',
          submitted_display_value: 'Yes',
        },
      },
    ]

    const blocks = guidanceTranscriptToDisplayBlocks(transcript)
    expect(blocks).toHaveLength(0)

    const items = buildCenterPanelTranscript([], transcript, 'pipe_wall_thickness_design')
    expect(items).toHaveLength(0)
  })

  it('does not inject client-only archived-prompt display output blocks', () => {
    const displayOutputs = [
      {
        id: 'archived-prompt-nominal_pipe_size',
        type: 'text' as const,
        content: 'Client-only archived prompt that must not appear.',
        variant: 'body' as const,
      },
    ]
    const transcript = [
      {
        block_id: 'archived-ask-nominal_pipe_size-FACT-002',
        kind: 'ask_archive',
        source: 'input_archive',
        text: 'Enter nominal pipe size (NPS).',
        payload: { display_role: 'ask_archive' },
      },
    ]

    const items = buildCenterPanelTranscript(displayOutputs, transcript, 'pipe_wall_thickness_design')
    const ids = items.map((item) => item.block.id)
    expect(ids).not.toContain('archived-ask-nominal_pipe_size-FACT-002')
    expect(ids).not.toContain('archived-prompt-nominal_pipe_size')
  })

  it('passes reference_chips through to text display blocks', () => {
    const blocks = guidanceTranscriptToDisplayBlocks([
      {
        block_id: 'guidance-pipe_wall_thickness_design-expansion-gate-intro',
        kind: 'guidance',
        source: 'guidance',
        text: 'Gate narration.',
        payload: { display_role: 'branch_narration' },
        reference_chips: [
          {
            ref_type: 'node',
            id: '304.1.1-a',
            label: '§304.1.1',
            target: { node_id: '304.1.1-a' },
          },
        ],
      },
    ])

    expect(blocks[0]?.reference_chips).toHaveLength(1)
    expect(blocks[0]?.reference_chips?.[0]?.label).toBe('§304.1.1')
  })
})
