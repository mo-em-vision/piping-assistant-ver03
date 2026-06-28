export interface MaterialOptionDto {
  value: string
  label: string
  standard: string
  specification: string
}

export interface MaterialSearchResponse {
  materials: MaterialOptionDto[]
  query: string
}

export interface MaterialMechanicalRowDto {
  test_temperature_f?: number
  tensile_strength_min?: { ksi?: number; pa?: number; value?: number }
  yield_strength_min?: { ksi?: number; pa?: number; value?: number }
  elongation_min_percent?: number
  reduction_of_area_min_percent?: number | null
}

export interface MaterialDetailDto {
  material_id: string
  display_name: string
  standard_slug: string
  grade_key: string
  specification: string
  product_form: string
  uns_number: string
  aliases: string[]
  mechanical_properties: {
    room_temperature?: MaterialMechanicalRowDto
    elevated_temperature?: MaterialMechanicalRowDto[]
  }
  chemical_composition: Record<string, unknown>
  physical_properties: Record<string, unknown>
  notes: string[]
  source_node: string
  table_id: string
}
