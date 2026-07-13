import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

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

const here = dirname(fileURLToPath(import.meta.url))
const registryPath = resolve(here, '../../../contracts/center_panel_output_block_types.json')

function loadRegistry(): CenterPanelBlockRegistry {
  return JSON.parse(readFileSync(registryPath, 'utf-8')) as CenterPanelBlockRegistry
}

const registry = loadRegistry()

export const CENTER_PANEL_BLOCK_TYPES = registry.block_types.map((entry) => entry.type) as readonly [
  'text',
  'warning',
  'paragraph_context',
  'result_summary',
  'applicability',
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
