import type { MaterialDetailDto, MaterialOptionDto } from '@/types/backend/materials'

/** MOCK_DATA — ASTM material suggestions for offline autocomplete. */
export const mockMaterialCatalog: MaterialOptionDto[] = [
  {
    value: 'astm_a106_gr_b',
    label: 'ASTM A106 Grade B',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'astm_a106_gr_a',
    label: 'ASTM A106 Grade A',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'astm_a106_gr_c',
    label: 'ASTM A106 Grade C',
    standard: 'astm_a106',
    specification: 'ASTM A106/A106M',
  },
  {
    value: 'astm_a312_tp304',
    label: 'ASTM A312 TP304',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'astm_a312_tp304l',
    label: 'ASTM A312 TP304L',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'astm_a312_tp316',
    label: 'ASTM A312 TP316',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
  {
    value: 'astm_a312_tp316l',
    label: 'ASTM A312 TP316L',
    standard: 'astm_a312',
    specification: 'ASTM A312/A312M',
  },
]

const mockMaterialDetails: Record<string, MaterialDetailDto> = {
  astm_a106_gr_b: {
    material_id: 'astm_a106_gr_b',
    display_name: 'ASTM A106 Grade B',
    standard_slug: 'astm_a106',
    grade_key: 'A106 Gr B',
    specification: 'ASTM A106/A106M',
    product_form: 'seamless_pipe',
    uns_number: 'K03006',
    aliases: ['A106B', 'SA-106B', 'SA-106 Grade B'],
    mechanical_properties: {
      room_temperature: {
        test_temperature_f: 70,
        tensile_strength_min: { ksi: 60, pa: 413685437 },
        yield_strength_min: { ksi: 35, pa: 241316505 },
        elongation_min_percent: 30,
      },
      elevated_temperature: [
        {
          test_temperature_f: 400,
          tensile_strength_min: { ksi: 58, pa: 399896758 },
          yield_strength_min: { ksi: 29, pa: 200048000 },
          elongation_min_percent: 25,
        },
      ],
    },
    chemical_composition: {
      unit: 'percent',
      limits: {
        carbon: { max: 0.3 },
        manganese: { min: 0.29, max: 1.06 },
        phosphorus: { max: 0.025 },
        sulfur: { max: 0.025 },
      },
    },
    physical_properties: {
      density_kg_m3: 7850,
      poisson_ratio: 0.3,
    },
    notes: ['Most common A106 grade for process piping and ASME B31.3 applications.'],
    source_node: 'ASTM-a106-material-properties',
    table_id: 'astm_a106_material_properties',
  },
}

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

export function getMockMaterialDetail(materialId: string): MaterialDetailDto {
  const detail = mockMaterialDetails[materialId]
  if (!detail) {
    throw new Error(`Mock material detail not found: ${materialId}`)
  }
  return detail
}
