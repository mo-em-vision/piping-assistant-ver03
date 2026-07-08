import type {
  DisplayOutputBlock,
  NextWorkflowSuggestionDto,
  NextWorkflowsOutputBlock,
  TextOutputBlock,
} from '@/types/backend/outputs'

export type FlowGuidancePresentationBlock = {
  block_id?: string
  kind?: string
  source?: string
  text?: string | null
  title?: string
  workflow_id?: string
  suggestions?: NextWorkflowSuggestionDto[]
  refs?: Record<string, string>
  payload?: {
    display_role?: string
    title?: string
    workflow_id?: string
    suggestions?: NextWorkflowSuggestionDto[]
  }
  reference_chips?: Array<{
    ref_type: 'node' | 'equation' | 'table' | 'paragraph'
    id: string
    label: string
    title?: string
    target: {
      node_id?: string
      equation_id?: string
      table_id?: string
      paragraph_id?: string
    }
  }>
}

const INTERNAL_TEXT_MARKERS = [
  'engineering_plan',
  'legacy_goal_map',
  'GOAL-',
  'REQ-',
  'waiting_user_input',
]

function isGuidanceNarrationBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'guidance' && block.source === 'guidance'
}

function isRuntimeTranscriptBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'text' && block.source === 'runtime'
}

function isInputArchiveBlock(block: FlowGuidancePresentationBlock): boolean {
  return (
    block.source === 'input_archive' &&
    (block.kind === 'ask_archive' || block.kind === 'answer_archive')
  )
}

function isNextWorkflowsBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'next_workflows' && block.source === 'workflow_runtime'
}

function isDurableTranscriptBlock(block: FlowGuidancePresentationBlock): boolean {
  return (
    isGuidanceNarrationBlock(block) ||
    isRuntimeTranscriptBlock(block) ||
    isInputArchiveBlock(block) ||
    isNextWorkflowsBlock(block)
  )
}

function inferTranscriptDisplayRole(block: FlowGuidancePresentationBlock): string {
  const fromPayload = block.payload?.display_role?.trim()
  if (fromPayload) {
    return fromPayload
  }
  const blockId = String(block.block_id ?? '')
  if (blockId.startsWith('next-workflows-')) {
    return 'next_workflows'
  }
  if (blockId.startsWith('archived-ask-')) {
    return 'ask_archive'
  }
  if (blockId.startsWith('archived-answer-')) {
    return 'answer_archive'
  }
  return inferGuidanceDisplayRole(block)
}

function inferGuidanceDisplayRole(block: FlowGuidancePresentationBlock): string {
  const fromPayload = block.payload?.display_role?.trim()
  if (fromPayload) {
    return fromPayload
  }
  const blockId = String(block.block_id ?? '')
  if (blockId.startsWith('workflow-intro-')) {
    return 'workflow_intro'
  }
  if (blockId.startsWith('result-summary-')) {
    return 'result_summary'
  }
  if (blockId.includes('parameter-gathering')) {
    return 'input_context'
  }
  return 'branch_narration'
}

function mapNextWorkflowsBlock(block: FlowGuidancePresentationBlock): NextWorkflowsOutputBlock | null {
  const blockId = String(block.block_id ?? '').trim()
  if (!blockId) {
    return null
  }
  const suggestions = block.suggestions ?? block.payload?.suggestions ?? []
  if (!Array.isArray(suggestions) || suggestions.length === 0) {
    return null
  }
  const title =
    String(block.title ?? block.payload?.title ?? 'Suggested next workflows').trim() ||
    'Suggested next workflows'
  const content = String(block.text ?? '').trim()
  return {
    id: blockId,
    type: 'next_workflows',
    title,
    content,
    suggestions,
    display_role: 'next_workflows',
    lifecycle: 'durable',
    history_eligible: true,
  }
}

/** Convert backend flow_guidance.transcript_blocks to scroll display blocks. */
export function guidanceTranscriptToDisplayBlocks(
  transcriptBlocks: unknown[],
): DisplayOutputBlock[] {
  if (!Array.isArray(transcriptBlocks)) {
    return []
  }

  const results: DisplayOutputBlock[] = []
  for (const raw of transcriptBlocks) {
    if (!raw || typeof raw !== 'object') {
      continue
    }
    const block = raw as FlowGuidancePresentationBlock
    if (!isDurableTranscriptBlock(block)) {
      continue
    }

    if (isNextWorkflowsBlock(block)) {
      const mapped = mapNextWorkflowsBlock(block)
      if (mapped) {
        results.push(mapped)
      }
      continue
    }

    const text = String(block.text ?? '').trim()
    if (!text) {
      continue
    }
    const blockId = String(block.block_id ?? '').trim()
    if (!blockId) {
      continue
    }
    const displayRole = inferTranscriptDisplayRole(block)
    const title =
      typeof block.payload?.title === 'string' ? block.payload.title.trim() : undefined
    const textBlock: TextOutputBlock = {
      id: blockId,
      type: 'text',
      content: text,
      ...(title ? { title } : {}),
      display_role: displayRole,
      lifecycle: 'durable',
      history_eligible: true,
      ...(Array.isArray(block.reference_chips) && block.reference_chips.length
        ? { reference_chips: block.reference_chips }
        : {}),
    }
    results.push(textBlock)
  }
  return results
}

export function containsInternalLeakText(text: string): boolean {
  const normalized = text.trim()
  if (!normalized) {
    return false
  }
  if (normalized.startsWith('{') && normalized.includes('"GOAL-')) {
    return true
  }
  return INTERNAL_TEXT_MARKERS.some((marker) => normalized.includes(marker))
}

export function assertUserVisibleText(text: string): boolean {
  return !containsInternalLeakText(text)
}
