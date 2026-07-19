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

function isEngineeringDecisionBlock(block: FlowGuidancePresentationBlock): boolean {
  return block.kind === 'text' && block.source === 'engineering_decision'
}

function isDurableTranscriptBlock(block: FlowGuidancePresentationBlock): boolean {
  return (
    isGuidanceNarrationBlock(block) ||
    isRuntimeTranscriptBlock(block) ||
    isWorkflowNodeTranscriptBlock(block) ||
    isEngineeringDecisionBlock(block) ||
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
  if (blockId.startsWith('engineering-decision-')) {
    return 'engineering_decision'
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

function slugFromPrefixedId(blockId: string, prefix: string): string | null {
  if (!blockId.startsWith(prefix)) {
    return null
  }
  const slug = blockId.slice(prefix.length).trim()
  return slug || null
}

function combineWorkflowIntroText(title: string, description: string): string {
  const titleText = title.trim()
  const descriptionText = description.trim()
  if (titleText && descriptionText) {
    return `${titleText}\n\n${descriptionText}`
  }
  return titleText || descriptionText
}

function syntheticWorkflowIntroBlock(
  workflowSlug: string,
  titleText: string,
  descriptionText: string,
): FlowGuidancePresentationBlock {
  const payload: FlowGuidancePresentationBlock['payload'] = {
    display_role: 'workflow_intro',
  }
  if (titleText.trim()) {
    payload.title = titleText.trim()
  }
  return {
    block_id: `workflow-intro-${workflowSlug}`,
    kind: 'text',
    source: 'workflow_node',
    text: combineWorkflowIntroText(titleText, descriptionText),
    payload,
  }
}

/** Project stored transcript blocks for display without mutating stored history. */
export function projectTranscriptBlocksForDisplay(
  transcriptBlocks: unknown[],
): FlowGuidancePresentationBlock[] {
  if (!Array.isArray(transcriptBlocks)) {
    return []
  }

  const rawBlocks = transcriptBlocks.filter(
    (raw): raw is FlowGuidancePresentationBlock => Boolean(raw && typeof raw === 'object'),
  )

  const titleBySlug = new Map<string, FlowGuidancePresentationBlock>()
  const descriptionBySlug = new Map<string, FlowGuidancePresentationBlock>()
  const nativeIntroSlugs = new Set<string>()

  for (const block of rawBlocks) {
    const blockId = String(block.block_id ?? '').trim()
    if (!blockId) {
      continue
    }
    const introSlug = slugFromPrefixedId(blockId, 'workflow-intro-')
    if (introSlug) {
      nativeIntroSlugs.add(introSlug)
      continue
    }
    const titleSlug = slugFromPrefixedId(blockId, 'workflow-title-')
    if (titleSlug) {
      titleBySlug.set(titleSlug, block)
      continue
    }
    const descriptionSlug = slugFromPrefixedId(blockId, 'workflow-description-')
    if (descriptionSlug) {
      descriptionBySlug.set(descriptionSlug, block)
    }
  }

  const consumedIds = new Set<string>()
  const syntheticBySlug = new Map<string, FlowGuidancePresentationBlock>()

  for (const slug of nativeIntroSlugs) {
    const titleBlock = titleBySlug.get(slug)
    const descriptionBlock = descriptionBySlug.get(slug)
    if (titleBlock?.block_id) {
      consumedIds.add(titleBlock.block_id)
    }
    if (descriptionBlock?.block_id) {
      consumedIds.add(descriptionBlock.block_id)
    }
  }

  const legacySlugs = new Set([...titleBySlug.keys(), ...descriptionBySlug.keys()])
  for (const slug of [...legacySlugs].sort()) {
    if (nativeIntroSlugs.has(slug)) {
      continue
    }
    const titleBlock = titleBySlug.get(slug)
    const descriptionBlock = descriptionBySlug.get(slug)
    const titleText = String(titleBlock?.text ?? '')
    const descriptionText = String(descriptionBlock?.text ?? '')
    if (!titleText.trim() && !descriptionText.trim()) {
      continue
    }
    syntheticBySlug.set(
      slug,
      syntheticWorkflowIntroBlock(slug, titleText, descriptionText),
    )
    if (titleBlock?.block_id) {
      consumedIds.add(titleBlock.block_id)
    }
    if (descriptionBlock?.block_id) {
      consumedIds.add(descriptionBlock.block_id)
    }
  }

  const projected: FlowGuidancePresentationBlock[] = []
  const insertedSynthetic = new Set<string>()

  for (const block of rawBlocks) {
    const blockId = String(block.block_id ?? '').trim()
    if (blockId && consumedIds.has(blockId)) {
      const slug =
        slugFromPrefixedId(blockId, 'workflow-title-') ??
        slugFromPrefixedId(blockId, 'workflow-description-')
      if (slug && syntheticBySlug.has(slug) && !insertedSynthetic.has(slug)) {
        projected.push(syntheticBySlug.get(slug)!)
        insertedSynthetic.add(slug)
      }
      continue
    }
    projected.push(block)
  }

  return projected
}

/** Convert backend flow_guidance.transcript_blocks to scroll display blocks. */
export function guidanceTranscriptToDisplayBlocks(
  transcriptBlocks: unknown[],
): DisplayOutputBlock[] {
  if (!Array.isArray(transcriptBlocks)) {
    return []
  }

  const projected = projectTranscriptBlocksForDisplay(transcriptBlocks)
  const results: DisplayOutputBlock[] = []
  for (const block of projected) {
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
    if (displayRole === 'title' || displayRole === 'workflow_description') {
      continue
    }
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
