export interface NodeTypeStyle {
  bg: string
  border: string
  label: string
}

export type NodeTypeColors = Record<string, NodeTypeStyle>

const _COLOR_BLUE = { bg: '#1e3a5f', border: '#3b82f6', label: 'Workflow' }
const _COLOR_PURPLE = { bg: '#3b1f4a', border: '#a855f7', label: 'Equation' }
const _COLOR_GREEN = { bg: '#1a3d2e', border: '#22c55e', label: 'Parameter' }
const _COLOR_AMBER = { bg: '#3d2f14', border: '#f59e0b', label: 'Standard' }
const _COLOR_RED = { bg: '#4a1f1f', border: '#ef4444', label: 'Validator' }
const _COLOR_CYAN = { bg: '#1f3d4a', border: '#06b6d4', label: 'Lookup' }
const _COLOR_SLATE = { bg: '#2d3748', border: '#94a3b8', label: 'Table' }
const _COLOR_GRAY = { bg: '#2a2a2a', border: '#737373', label: 'Text' }
const _COLOR_TEAL = { bg: '#134e4a', border: '#2dd4bf', label: 'Unit' }

export const NODE_TYPE_COLORS: NodeTypeColors = {
  workflow: _COLOR_BLUE,
  equation: _COLOR_PURPLE,
  parameter: _COLOR_GREEN,
  standard_section: _COLOR_AMBER,
  assumption: _COLOR_RED,
  interaction: { bg: '#4a1f1f', border: '#f87171', label: 'Validator' },
  lookup: _COLOR_CYAN,
  table: _COLOR_SLATE,
  text: _COLOR_GRAY,
  unit: _COLOR_TEAL,
  calculation: { bg: '#3b1f4a', border: '#c084fc', label: 'Calculator' },
  unknown: { bg: '#1f1f1f', border: '#525252', label: 'Unknown' },
}

const KIND_STYLE_OVERRIDES: Record<string, NodeTypeStyle> = {
  lookup: _COLOR_CYAN,
  section: _COLOR_AMBER,
  table: _COLOR_SLATE,
  assumption: _COLOR_RED,
  interaction: { bg: '#4a1f1f', border: '#f87171', label: 'Validator' },
  calculation: _COLOR_PURPLE,
}

const DISPLAY_COLOR_MAP: Record<string, { bg: string; border: string }> = {
  blue: { bg: '#1e3a5f', border: '#3b82f6' },
  green: { bg: '#1a3d2e', border: '#22c55e' },
  purple: { bg: '#3b1f4a', border: '#a855f7' },
  amber: { bg: '#3d2f14', border: '#f59e0b' },
  red: { bg: '#4a1f1f', border: '#ef4444' },
  cyan: { bg: '#1f3d4a', border: '#06b6d4' },
  teal: { bg: '#134e4a', border: '#2dd4bf' },
}

export const EDGE_TYPE_COLORS: Record<string, string> = {
  requires: '#60a5fa',
  depends_on: '#60a5fa',
  calculates: '#c084fc',
  computed_from: '#c084fc',
  derived_from: '#c084fc',
  outputs: '#34d399',
  references: '#fbbf24',
  uses: '#22d3ee',
  validates: '#f87171',
  contains: '#a3a3a3',
  anchors_to: '#f59e0b',
  located_in: '#f59e0b',
  defines: '#a78bfa',
  explains: '#94a3b8',
  next_step: '#38bdf8',
  uses_table: '#2dd4bf',
  converts_to: '#2dd4bf',
  accepts: '#34d399',
  default: '#64748b',
}

export const ALL_NODE_TYPES = Object.keys(NODE_TYPE_COLORS)

export function nodeStyle(
  nodeType: string,
  kind?: string | null,
  display?: { color?: string; label?: string } | null,
): NodeTypeStyle {
  const base = NODE_TYPE_COLORS[nodeType] ?? NODE_TYPE_COLORS.unknown
  const kindStyle = kind ? KIND_STYLE_OVERRIDES[kind] : undefined
  let style = kindStyle ?? base

  if (display?.color) {
    const palette = DISPLAY_COLOR_MAP[display.color.toLowerCase()]
    if (palette) {
      style = {
        ...style,
        bg: palette.bg,
        border: palette.border,
      }
    }
  }
  if (display?.label) {
    style = { ...style, label: display.label }
  }
  return style
}

export const EXECUTION_STATE_COLORS: Record<string, { bg: string; border: string }> = {
  pending: { bg: '#2a2a2a', border: '#737373' },
  active: { bg: '#1e3a5f', border: '#3b82f6' },
  success: { bg: '#1a3d2e', border: '#22c55e' },
  skipped: { bg: '#3d2f14', border: '#f59e0b' },
  failed: { bg: '#4a1f1f', border: '#ef4444' },
}

export function executionStateStyle(state?: string | null): { bg: string; border: string } | null {
  if (!state) {
    return null
  }
  return EXECUTION_STATE_COLORS[state] ?? null
}
