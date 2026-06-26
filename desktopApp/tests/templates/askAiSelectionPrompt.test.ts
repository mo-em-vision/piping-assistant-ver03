import { describe, expect, it } from 'vitest'

import { mockTaskState } from '@/mock/taskState.mock'
import {
  ASK_AI_SELECTION_PROMPT_TEMPLATE,
  buildAskAiSelectionPrompt,
} from '@/templates/askAiSelectionPrompt'
import { buildAskAiTaskStateBrief } from '@/templates/buildAskAiTaskStateBrief'

describe('buildAskAiTaskStateBrief', () => {
  it('summarizes workflow progress and visible workspace content', () => {
    const brief = buildAskAiTaskStateBrief(mockTaskState, 'Refinery Expansion')

    expect(brief).toContain('Project: Refinery Expansion')
    expect(brief).toContain('Pipe Thickness Calculation')
    expect(brief).toContain('pipe_wall_thickness_design')
    expect(brief).toContain('Inputs already provided:')
    expect(brief).toContain('Visible workspace content:')
    expect(brief).toContain('Governing equation')
  })
})

describe('buildAskAiSelectionPrompt', () => {
  it('asks for clarification with task state and selected text', () => {
    const prompt = buildAskAiSelectionPrompt({
      selectedText: 't = 12.5 mm',
      taskState: mockTaskState,
      projectName: 'Refinery Expansion',
    })

    expect(prompt).toContain('clarification')
    expect(prompt).toContain('definitions')
    expect(prompt).toContain('examples')
    expect(prompt).toContain('## Current task state')
    expect(prompt).toContain('Pipe Thickness Calculation')
    expect(prompt).toContain('t = 12.5 mm')
    expect(prompt).not.toContain('{{')
  })

  it('uses empty strings for missing optional fields', () => {
    const prompt = buildAskAiSelectionPrompt({
      selectedText: 'Selected only',
    })

    expect(prompt).toContain('Selected only')
    expect(prompt).toContain('No task state is available.')
    expect(prompt).not.toContain('{{')
    expect(ASK_AI_SELECTION_PROMPT_TEMPLATE).toContain('{{selectedText}}')
  })
})
