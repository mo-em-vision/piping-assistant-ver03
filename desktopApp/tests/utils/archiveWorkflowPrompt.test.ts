import { describe, expect, it } from 'vitest'

import { mockTaskState } from '@/mock/taskState.mock'
import {
  buildArchivedPromptBlock,
  injectArchivedPrompt,
  resolveArchivedParameterId,
} from '@/utils/archiveWorkflowPrompt'
import { withPreservedDisplayOutputs } from '@/store/taskStore'

describe('archiveWorkflowPrompt', () => {
  it('builds an archived text block for a submitted parameter prompt', () => {
    const previous = {
      ...mockTaskState,
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size for the straight section.',
      },
    }

    const block = buildArchivedPromptBlock(previous, 'nominal_pipe_size')

    expect(block).toEqual({
      id: 'archived-prompt-nominal_pipe_size',
      type: 'text',
      content: 'Select the nominal pipe size for the straight section.',
      variant: 'body',
    })
  })

  it('resolves archived parameter id when ask advances to the next parameter', () => {
    const previous = {
      ...mockTaskState,
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size.',
      },
    }
    const incoming = {
      ...mockTaskState,
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'design_temperature',
        prompt: 'Enter design temperature.',
      },
    }

    expect(resolveArchivedParameterId(previous, incoming)).toBe('nominal_pipe_size')
  })

  it('injects archived prompt into incoming display outputs', () => {
    const previous = {
      ...mockTaskState,
      display_outputs: [],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size.',
      },
    }
    const incoming = {
      ...mockTaskState,
      display_outputs: [],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'design_temperature',
        prompt: 'Enter design temperature.',
      },
    }

    const enriched = injectArchivedPrompt(previous, incoming, 'nominal_pipe_size')

    expect(enriched.display_outputs).toEqual([
      {
        id: 'archived-prompt-nominal_pipe_size',
        type: 'text',
        content: 'Select the nominal pipe size.',
        variant: 'body',
      },
    ])
  })

  it('does not duplicate archived prompts on subsequent merges', () => {
    const archived = {
      id: 'archived-prompt-nominal_pipe_size',
      type: 'text' as const,
      content: 'Select the nominal pipe size.',
      variant: 'body' as const,
    }
    const previous = {
      ...mockTaskState,
      display_outputs: [archived],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'design_temperature',
        prompt: 'Enter design temperature.',
      },
    }
    const incoming = {
      ...mockTaskState,
      display_outputs: [],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'design_temperature',
        prompt: 'Enter design temperature.',
      },
    }

    const enriched = injectArchivedPrompt(previous, incoming, 'nominal_pipe_size')

    expect(enriched.display_outputs).toEqual([])
  })
})

describe('withPreservedDisplayOutputs prompt archival', () => {
  it('appends superseded prompt blocks into the merged transcript', () => {
    const previous = {
      ...mockTaskState,
      display_outputs: [
        {
          id: 'preview-equation',
          type: 'equation' as const,
          content: 't = PD / 2(SEW + PY)',
          display: 't = PD / 2(SEW + PY)',
        },
      ],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'nominal_pipe_size',
        prompt: 'Select the nominal pipe size.',
      },
    }
    const incoming = {
      ...mockTaskState,
      display_outputs: [],
      current_ask: {
        kind: 'input' as const,
        parameter_id: 'design_temperature',
        prompt: 'Enter design temperature.',
      },
    }

    const merged = withPreservedDisplayOutputs(previous, incoming, {
      submittedParameter: 'nominal_pipe_size',
    })

    expect(merged.display_outputs.some((block) => block.id === 'preview-equation')).toBe(true)
    expect(merged.display_outputs.some((block) => block.id === 'archived-prompt-nominal_pipe_size')).toBe(
      true,
    )
    expect(
      merged.display_outputs.find((block) => block.id === 'archived-prompt-nominal_pipe_size')?.type ===
        'text' &&
        (merged.display_outputs.find((block) => block.id === 'archived-prompt-nominal_pipe_size') as {
          content?: string
        }).content === 'Select the nominal pipe size.',
    ).toBe(true)
  })
})
