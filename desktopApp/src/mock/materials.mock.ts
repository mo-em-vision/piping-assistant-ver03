import type { MaterialOptionDto } from '@/types/backend/materials'

/** MOCK_DATA — ASTM material suggestions for offline autocomplete. */
export const mockMaterialCatalog: MaterialOptionDto[] = [
  {
    value: 'SA-106B',
    label: 'ASTM A106 Grade B',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'SA-106A',
    label: 'ASTM A106 Grade A',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'SA-106C',
    label: 'ASTM A106 Grade C',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'A106 Gr B',
    label: 'ASTM A106 Grade B',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'TP304',
    label: 'ASTM A312 TP304',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'TP304L',
    label: 'ASTM A312 TP304L',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'TP316',
    label: 'ASTM A312 TP316',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'TP316L',
    label: 'ASTM A312 TP316L',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'SS316',
    label: 'ASTM A312 TP316',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
]

export function searchMockMaterials(query: string, limit = 12): MaterialOptionDto[] {
  const needle = query.trim().toLowerCase()
  if (needle.length < 3) {
    return []
  }

  const matches = mockMaterialCatalog.filter((item) => {
    const haystack = `${item.value} ${item.label} ${item.specification}`.toLowerCase()
    return haystack.includes(needle)
  })

  matches.sort((left, right) => {
    const leftStarts = left.value.toLowerCase().startsWith(needle) ? 0 : 1
    const rightStarts = right.value.toLowerCase().startsWith(needle) ? 0 : 1
    return leftStarts - rightStarts || left.value.localeCompare(right.value)
  })

  return matches.slice(0, limit)
}
