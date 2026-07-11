import type { DisplayOutputBlock } from '@/types/backend/outputs'
import roleOrderJson from '../../../contracts/center_panel_report_role_order.json'

export const REPORT_ROLE_ORDER = roleOrderJson as readonly string[]

export type DisplayRole = (typeof REPORT_ROLE_ORDER)[number]

export const DISPLAY_STATE_ORDER = ['active', 'preview', 'evaluated'] as const
export type DisplayState = (typeof DISPLAY_STATE_ORDER)[number]

export const EQUATION_CONTENT_ORDER = ['symbolic', 'substituted', 'evaluated'] as const
export type EquationContent = (typeof EQUATION_CONTENT_ORDER)[number]

export type DisplayBlockWithRole = DisplayOutputBlock & {
  display_role?: string
  display_state?: DisplayState
  equation_content?: EquationContent
  lifecycle?: 'durable' | 'preview' | 'volatile'
  display_channel?: string
  result_kind?: string
}

const CANONICAL_ROLES = new Set<string>(REPORT_ROLE_ORDER)

export function isCanonicalDisplayRole(role: string | undefined | null): boolean {
  return Boolean(role && CANONICAL_ROLES.has(role))
}

export function reportRoleIndex(displayRole: string | undefined | null): number {
  const role = String(displayRole ?? '').trim()
  if (!role) {
    return REPORT_ROLE_ORDER.length
  }
  const index = REPORT_ROLE_ORDER.indexOf(role as DisplayRole)
  return index === -1 ? REPORT_ROLE_ORDER.length : index
}

export function displayStateIndex(displayState: string | undefined | null): number {
  const state = String(displayState ?? '').trim()
  if (!state) {
    return DISPLAY_STATE_ORDER.length
  }
  const index = DISPLAY_STATE_ORDER.indexOf(state as DisplayState)
  return index === -1 ? DISPLAY_STATE_ORDER.length : index
}

export function lifecycleForEquationState(displayState: string | undefined | null): 'durable' | 'preview' {
  return displayState === 'evaluated' ? 'durable' : 'preview'
}

export function inferEquationContent(block: DisplayBlockWithRole): EquationContent {
  const explicit = block.equation_content
  if (explicit && EQUATION_CONTENT_ORDER.includes(explicit)) {
    return explicit
  }

  const trace = block.equation_display_trace as
    | { status?: string; result?: unknown; substituted_latex?: string }
    | undefined

  if (trace?.status === 'evaluated' || trace?.result) {
    return 'evaluated'
  }
  if (trace?.substituted_latex || block.substituted_latex) {
    return 'substituted'
  }
  return 'symbolic'
}

export function inferDisplayState(block: DisplayBlockWithRole): DisplayState {
  const explicit = block.display_state
  if (explicit && DISPLAY_STATE_ORDER.includes(explicit)) {
    return explicit
  }

  const id = block.id ?? ''
  if (block.lifecycle === 'durable' && id.startsWith('equation-') && !id.startsWith('equation-trace-')) {
    return 'evaluated'
  }
  if (id.startsWith('node-activation-equation-')) {
    return 'active'
  }
  if (id.startsWith('path-preview-equation-')) {
    return 'preview'
  }
  if (id.startsWith('equation-trace-')) {
    return 'evaluated'
  }
  if (id.startsWith('equation-')) {
    return block.input_table || block.result ? 'evaluated' : 'preview'
  }
  return 'preview'
}

export function inferDisplayFieldsFromBlock(block: DisplayBlockWithRole): DisplayBlockWithRole {
  const resolved: DisplayBlockWithRole = { ...block }
  const id = block.id ?? ''

  if (id.startsWith('workflow-intro-')) {
    resolved.display_role = 'workflow_intro'
  } else if (id.startsWith('result-summary-')) {
    resolved.display_role = 'result_summary'
  } else if (id.startsWith('path-preview-intro-')) {
    resolved.display_role = 'node_intro'
  } else if (id.startsWith('table-lookup-')) {
    resolved.display_role = block.highlight_row
      ? 'lookup_table_recommendation'
      : 'engineering_reference'
  } else if (id.startsWith('paragraph-')) {
    resolved.display_role =
      block.display_role === 'paragraph_context' ? 'paragraph_context' : 'engineering_reference'
  } else if (id.startsWith('validation-')) {
    resolved.display_role = 'applicability'
  } else if (
    id.startsWith('equation-') ||
    id.startsWith('path-preview-equation-') ||
    id.startsWith('node-activation-equation-')
  ) {
    resolved.display_role = 'equation'
  } else if (block.type === 'warning' || block.variant === 'warning') {
    resolved.display_role = 'warning'
  }

  if (resolved.display_role === 'equation') {
    resolved.display_state = inferDisplayState(resolved)
    resolved.equation_content = inferEquationContent(resolved)
    resolved.lifecycle = lifecycleForEquationState(resolved.display_state)
  }

  return resolved
}

export function resolveDisplayBlock(block: DisplayBlockWithRole): DisplayBlockWithRole {
  const role = String(block.display_role ?? '').trim()
  let resolved: DisplayBlockWithRole

  if (role && isCanonicalDisplayRole(role)) {
    resolved = { ...block }
  } else if (role) {
    resolved = { ...block }
  } else {
    resolved = inferDisplayFieldsFromBlock(block)
  }

  if (resolved.display_role === 'equation') {
    resolved.display_state = inferDisplayState(resolved)
    resolved.equation_content = inferEquationContent(resolved)
    resolved.lifecycle = lifecycleForEquationState(resolved.display_state)
  }

  return resolved
}

export function blockDisplayRole(block: DisplayOutputBlock): string {
  return resolveDisplayBlock(block as DisplayBlockWithRole).display_role ?? ''
}
