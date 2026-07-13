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

function isWorkflowNodeTranscriptBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'text' && block.source === 'workflow_node'
}

function isNextWorkflowsBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'next_workflows' && block.source === 'workflow_runtime'
}

function isDurableTranscriptBlock(block: FlowGuidancePresentationBlock): boolean {
  return (
    isGuidanceNarrationBlock(block) ||
    isRuntimeTranscriptBlock(block) ||
    isWorkflowNodeTranscriptBlock(block) ||
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
  if (blockId.startsWith('workflow-title-')) {
    return 'title'
  }
  if (blockId.startsWith('workflow-description-')) {
    return 'workflow_description'
  }
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

function mapDisplayRoleToBlockType(displayRole: string): DisplayOutputBlock['type'] {
  switch (displayRole) {
    case 'warning':
      return 'warning'
    case 'paragraph_context':
      return 'paragraph_context'
    case 'result_summary':
      return 'result_summary'
    default:
      return 'text'
  }
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
  const relatedLabel =
    String(
      (block as { related_workflow_label?: string }).related_workflow_label ??
        block.payload?.related_workflow_label ??
        'Related Workflows',
    ).trim() || 'Related Workflows'
  return {
    id: blockId,
    type: 'next_workflows',
    related_workflow_label: relatedLabel,
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
    const blockType = mapDisplayRoleToBlockType(displayRole)
    const textBlock = {
      id: blockId,
      type: blockType,
      content: text,
      ...(title ? { title } : {}),
      display_role: displayRole,
      lifecycle: 'durable',
      history_eligible: true,
      ...(Array.isArray(block.reference_chips) && block.reference_chips.length
        ? {
            reference_chips: block.reference_chips,
            reference_links_placement: 'inline' as const,
          }
        : {}),
    }
    results.push(textBlock as DisplayOutputBlock)
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
