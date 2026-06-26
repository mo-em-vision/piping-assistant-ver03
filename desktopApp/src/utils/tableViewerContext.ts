import type { TableViewerContext } from '@/store/rightPanelStore'
import type { TaskStateDto } from '@/types/backend/api'

function inputDisplayValue(
  inputs: Record<string, unknown>,
  key: string,
): string | undefined {
  const entry = inputs[key]
  if (!entry || typeof entry !== 'object') {
    return undefined
  }
  const record = entry as { display_value?: string | null; value?: unknown }
  if (record.display_value) {
    return String(record.display_value)
  }
  if (record.value != null && record.value !== '') {
    return String(record.value)
  }
  return undefined
}

function normalizeTableKey(tableId: string): string {
  return tableId
    .toLowerCase()
    .replace(/^asme_b31\.3_/, '')
    .replace(/^table_/, '')
    .replace(/_/g, '-')
}

export function buildTableViewerContext(
  tableId: string,
  taskState?: TaskStateDto | null,
): TableViewerContext | undefined {
  if (!taskState?.inputs) {
    return undefined
  }

  const inputs = taskState.inputs
  const key = normalizeTableKey(tableId)
  const material = inputDisplayValue(inputs, 'material')
  const temperature = inputDisplayValue(inputs, 'design_temperature')
  const jointCategory = inputDisplayValue(inputs, 'joint_category')

  if (key === '304-1-1' || key === '304.1.1') {
    if (!temperature) {
      return undefined
    }
    return {
      highlightKeys: {
        material: material ?? '',
        design_temperature: temperature,
        temperature_c: temperature,
      },
    }
  }

  if (key === 'a-1' || key === 'a-1a' || key === 'a-1b') {
    const highlightKeys: Record<string, string> = {}
    if (material) {
      highlightKeys.material = material
    }
    if (jointCategory && (key === 'a-1a' || key === 'a-1b')) {
      highlightKeys.joint_category = jointCategory
    }
    if (temperature && key === 'a-1') {
      highlightKeys.design_temperature = temperature
    }
    if (Object.keys(highlightKeys).length === 0) {
      return undefined
    }
    return { highlightKeys }
  }

  if (key === '302.3.5' || key === '302-3-5') {
    if (!material) {
      return undefined
    }
    return {
      highlightKeys: { material },
    }
  }

  return undefined
}
