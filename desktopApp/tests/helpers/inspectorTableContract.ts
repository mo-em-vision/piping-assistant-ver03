import { expect } from 'vitest'

import { assertUserVisibleText } from '@/utils/flowGuidanceTranscript'

const RAW_JSON_MARKERS = [
  '"requirements"',
  '"root_goal"',
  '"traversal"',
  'engineering_plan',
  'legacy_goal_map',
  'canonical_task_state',
]

const MAX_NORMAL_TABLE_CELL_CHARS = 240

export function looksLikeRawJsonBlob(text: string): boolean {
  const normalized = text.trim()
  if (!normalized) {
    return false
  }
  if (!assertUserVisibleText(normalized)) {
    return true
  }
  if (
    (normalized.startsWith('{') || normalized.startsWith('[')) &&
    RAW_JSON_MARKERS.some((marker) => normalized.includes(marker))
  ) {
    return true
  }
  if (
    (normalized.startsWith('{') && normalized.endsWith('}')) ||
    (normalized.startsWith('[') && normalized.endsWith(']'))
  ) {
    return normalized.length > MAX_NORMAL_TABLE_CELL_CHARS
  }
  return false
}

export function assertNormalInspectorTableCells(container: HTMLElement): void {
  const tables = container.querySelectorAll('table.inspector-table')
  expect(tables.length).toBeGreaterThan(0)

  tables.forEach((table) => {
    table.querySelectorAll('td').forEach((cell) => {
      const text = cell.textContent?.trim() ?? ''
      if (!text) {
        return
      }
      expect(
        assertUserVisibleText(text),
        `planner blob in inspector table cell: ${text.slice(0, 120)}`,
      ).toBe(true)
      expect(
        looksLikeRawJsonBlob(text),
        `raw JSON leaked into normal table row: ${text.slice(0, 120)}`,
      ).toBe(false)
      expect(
        text.length,
        `table cell too long for normal display (likely raw JSON): ${text.slice(0, 80)}…`,
      ).toBeLessThanOrEqual(MAX_NORMAL_TABLE_CELL_CHARS)
    })
  })

  expect(container.querySelectorAll('table.inspector-table td pre').length).toBe(0)
}

export function assertPlannerDebugRowsExcludeRawJson(container: HTMLElement): void {
  container
    .querySelectorAll('.planner-debug__row-label, .planner-debug__line, .planner-debug__goal-list li')
    .forEach((node) => {
      const text = node.textContent?.trim() ?? ''
      if (!text) {
        return
      }
      expect(assertUserVisibleText(text), `planner blob in debug row: ${text}`).toBe(true)
      expect(looksLikeRawJsonBlob(text), `raw JSON in planner debug row: ${text}`).toBe(false)
    })

  container.querySelectorAll('.planner-debug__row-id').forEach((node) => {
    const text = node.textContent?.trim() ?? ''
    if (!text) {
      return
    }
    expect(looksLikeRawJsonBlob(text), `raw JSON in planner debug row id: ${text}`).toBe(false)
    expect(
      text.length,
      `planner debug row id too long for normal display: ${text.slice(0, 80)}…`,
    ).toBeLessThanOrEqual(MAX_NORMAL_TABLE_CELL_CHARS)
  })

  expect(container.querySelectorAll('.planner-debug pre.inspector-code').length).toBe(0)
}

export function assertRawJsonLimitedToAdvancedSections(container: HTMLElement): void {
  const advancedBlocks = container.querySelectorAll('.inspector-advanced pre.inspector-code')
  expect(advancedBlocks.length).toBeGreaterThan(0)
}
