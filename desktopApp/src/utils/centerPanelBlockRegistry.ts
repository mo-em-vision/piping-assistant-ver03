import registryJson from '../../../contracts/center_panel_output_block_types.json'

export type CenterPanelBlockRegistryEntry = {
  type: string
  label: string
  desktop_component: string
  notes?: string
}

export type CenterPanelBlockRegistry = {
  version: number
  description?: string
  block_types: CenterPanelBlockRegistryEntry[]
}

// #region agent log
let registry: CenterPanelBlockRegistry
try {
  fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
    body: JSON.stringify({
      sessionId: 'ed32ea',
      location: 'centerPanelBlockRegistry.ts:pre-load',
      message: 'Attempting registry load from bundled JSON import',
      data: { source: 'contracts/center_panel_output_block_types.json' },
      timestamp: Date.now(),
      hypothesisId: 'B',
      runId: 'post-fix',
    }),
  }).catch(() => {})
  registry = registryJson as CenterPanelBlockRegistry
  fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
    body: JSON.stringify({
      sessionId: 'ed32ea',
      location: 'centerPanelBlockRegistry.ts:post-load',
      message: 'Registry loaded successfully',
      data: { blockTypeCount: registry.block_types.length },
      timestamp: Date.now(),
      hypothesisId: 'B',
      runId: 'post-fix',
    }),
  }).catch(() => {})
} catch (error) {
  fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'ed32ea' },
    body: JSON.stringify({
      sessionId: 'ed32ea',
      location: 'centerPanelBlockRegistry.ts:load-error',
      message: 'Registry load failed',
      data: { error: error instanceof Error ? error.message : String(error) },
      timestamp: Date.now(),
      hypothesisId: 'A',
      runId: 'post-fix',
    }),
  }).catch(() => {})
  throw error
}
// #endregion
export const CENTER_PANEL_BLOCK_TYPES = registry.block_types.map((entry) => entry.type) as readonly [
  'text',
  'warning',
  'paragraph_context',
  'result_summary',
  'equation',
  'table',
  'reference',
  'result',
  'next_workflows',
]

export type CenterPanelBlockType = (typeof CENTER_PANEL_BLOCK_TYPES)[number]

export const CENTER_PANEL_BLOCK_REGISTRY: CenterPanelBlockRegistry = registry

export const OUTPUT_RENDERER_COMPONENT_BY_TYPE: Record<CenterPanelBlockType, string> =
  Object.fromEntries(
    registry.block_types.map((entry) => [entry.type, entry.desktop_component]),
  ) as Record<CenterPanelBlockType, string>

export function isRegisteredCenterPanelBlockType(
  value: string,
): value is CenterPanelBlockType {
  return (CENTER_PANEL_BLOCK_TYPES as readonly string[]).includes(value)
}

export function filterRegisteredCenterPanelBlocks<T extends { type?: string | null }>(
  blocks: T[],
): T[] {
  return blocks.filter((block) => isRegisteredCenterPanelBlockType(String(block.type ?? '').trim()))
}

export function assertRegisteredCenterPanelBlockTypes(
  blocks: Array<{ type?: string | null; id?: string | null }>,
  context = 'center panel blocks',
): void {
  const allowed = new Set(CENTER_PANEL_BLOCK_TYPES)
  for (const [index, block] of blocks.entries()) {
    const blockType = String(block.type ?? '').trim()
    if (!blockType) {
      throw new Error(`${context}: block at index ${index} is missing type`)
    }
    if (!allowed.has(blockType as CenterPanelBlockType)) {
      throw new Error(
        `${context}: unregistered block type ${blockType} (allowed: ${[...allowed].join(', ')})`,
      )
    }
  }
}
