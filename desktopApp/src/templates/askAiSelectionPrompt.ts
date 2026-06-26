import { buildAskAiTaskStateBrief } from './buildAskAiTaskStateBrief'

import type { TaskStateDto } from '@/types/backend/api'

export interface AskAiSelectionContext {
  selectedText: string
  taskState?: TaskStateDto | null
  taskName?: string
  taskId?: string
  workflowId?: string
  currentStepId?: string | null
  discipline?: string
  activeNodeHeading?: string
  projectName?: string
  taskStateBrief?: string
}

export const ASK_AI_SELECTION_PROMPT_TEMPLATE = `The user is reviewing an engineering task and highlighted text they do not fully understand. They are looking for clarification, a plain-language explanation, definitions of technical terms, and practical examples related to their current work.

## Current task state
{{taskStateBrief}}

## Selected text
"""
{{selectedText}}
"""

Respond by helping the user understand the selected text in the context above. Provide:
1. A clear explanation of what the selected text means here
2. Definitions for any symbols, terms, or standards references involved
3. A brief example or analogy when it would make the idea easier to grasp
4. Any caveats that matter for this workflow step

Stay educational and focused on the selection. Do not restart the workflow or ask for new engineering inputs unless it is essential to explain the concept.`

function replacePlaceholders(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_match, key: string) => values[key] ?? '')
}

export function buildAskAiSelectionPrompt(context: AskAiSelectionContext): string {
  const taskStateBrief =
    context.taskStateBrief ??
    buildAskAiTaskStateBrief(context.taskState, context.projectName)

  return replacePlaceholders(ASK_AI_SELECTION_PROMPT_TEMPLATE, {
    selectedText: context.selectedText,
    taskStateBrief,
    taskName: context.taskName ?? '',
    taskId: context.taskId ?? '',
    workflowId: context.workflowId ?? '',
    currentStepId: context.currentStepId ?? '',
    discipline: context.discipline ?? '',
    activeNodeHeading: context.activeNodeHeading ?? '',
    projectName: context.projectName ?? '',
  }).trim()
}
