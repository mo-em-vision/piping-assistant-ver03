import {
  DEFAULT_WORKFLOW_ASK_PROMPT,
  getWorkflowAsk,
  parameterNamesMatch,
  type WorkflowAskKind,
} from '@/components/workflow/workflowAsk'
import { buildTaskStateViewModel } from '@/store/taskStateManager'
import type { TaskStateDto } from '@/types/backend/api'
import type { DisplayOutputBlock } from '@/types/backend/outputs'

import { mergeDisplayOutputs } from '@/utils/mergeDisplayOutputs'

function archivableAskKind(kind: WorkflowAskKind): boolean {
  return kind === 'input' || kind === 'clarify'
}

function archivedPromptId(parameterId: string): string {
  return `archived-prompt-${parameterId}`
}

function archivedPromptBlock(parameterId: string, prompt: string): DisplayOutputBlock {
  return {
    id: archivedPromptId(parameterId),
    type: 'text',
    content: prompt,
    variant: 'body',
  }
}

export function resolveArchivedParameterId(
  previous: TaskStateDto,
  incoming: TaskStateDto,
  submittedParameter?: string,
): string | undefined {
  if (submittedParameter) {
    return submittedParameter
  }

  const prevAsk = previous.current_ask
  if (!prevAsk || !archivableAskKind(prevAsk.kind)) {
    return undefined
  }

  const nextAsk = incoming.current_ask
  const prevParameterId = prevAsk.parameter_id ?? undefined

  if (prevAsk.kind === 'clarify') {
    if (nextAsk?.kind !== 'clarify') {
      return 'clarify'
    }
    return undefined
  }

  if (!prevParameterId) {
    return undefined
  }

  if (nextAsk?.parameter_id && !parameterNamesMatch(nextAsk.parameter_id, prevParameterId)) {
    return prevParameterId
  }

  const previousParameter = previous.parameters.find((item) =>
    parameterNamesMatch(prevParameterId, item.name),
  )
  const incomingParameter = incoming.parameters.find((item) =>
    parameterNamesMatch(prevParameterId, item.name),
  )
  if (
    previousParameter &&
    incomingParameter &&
    previousParameter.status !== 'confirmed' &&
    incomingParameter.status === 'confirmed'
  ) {
    return prevParameterId
  }

  return undefined
}

function promptForArchivedParameter(state: TaskStateDto, parameterId: string): string | null {
  const viewModel = buildTaskStateViewModel(state)
  const timeline = viewModel?.timeline ?? []
  const ask = getWorkflowAsk(state, timeline)

  if (ask.parameter && parameterNamesMatch(parameterId, ask.parameter.name) && ask.prompt?.trim()) {
    return ask.prompt.trim()
  }

  const currentAsk = state.current_ask
  if (
    currentAsk?.parameter_id &&
    parameterNamesMatch(currentAsk.parameter_id, parameterId) &&
    currentAsk.prompt?.trim()
  ) {
    return currentAsk.prompt.trim()
  }

  const parameter = state.parameters.find((item) => parameterNamesMatch(parameterId, item.name))
  const guidance = parameter?.guidance?.trim()
  if (guidance) {
    return guidance
  }

  const restoredTimeline = timeline.map((step) => {
    if (parameterNamesMatch(step.id, parameterId)) {
      return { ...step, status: 'active' as const }
    }
    if (step.status === 'active') {
      return { ...step, status: 'pending' as const }
    }
    return step
  })
  const restoredAsk = getWorkflowAsk(state, restoredTimeline)
  return restoredAsk.prompt?.trim() ?? null
}

export function buildArchivedPromptBlock(
  previous: TaskStateDto,
  parameterId: string,
): DisplayOutputBlock | null {
  const prompt = promptForArchivedParameter(previous, parameterId)
  if (!prompt || prompt === DEFAULT_WORKFLOW_ASK_PROMPT) {
    return null
  }

  return archivedPromptBlock(parameterId, prompt)
}

export function injectArchivedPrompt(
  previous: TaskStateDto | null,
  incoming: TaskStateDto,
  submittedParameter?: string,
): TaskStateDto {
  if (!previous || previous.task_id !== incoming.task_id) {
    return incoming
  }

  const parameterId = resolveArchivedParameterId(previous, incoming, submittedParameter)
  if (!parameterId) {
    return incoming
  }

  const blockId = archivedPromptId(parameterId)
  if ((previous.display_outputs ?? []).some((block) => block.id === blockId)) {
    return incoming
  }

  const archived = buildArchivedPromptBlock(previous, parameterId)
  if (!archived) {
    return incoming
  }

  return {
    ...incoming,
    display_outputs: mergeDisplayOutputs(incoming.display_outputs ?? [], [archived]),
  }
}
