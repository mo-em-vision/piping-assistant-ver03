export type ParameterType =
  | 'number'
  | 'text'
  | 'dropdown'
  | 'multi_select'
  | 'checkbox'
  | 'material'
  | 'unit'

export type ParameterStatus = 'pending' | 'confirmation_required' | 'confirmed'

export interface ParameterOptionDto {
  value: string
  label: string
}

export interface ParameterValidationDto {
  min?: number
  max?: number
}

export interface ParameterDefinitionDto {
  name: string
  label: string
  type: ParameterType
  required: boolean
  units: string[]
  default_unit: string
  default_value: unknown
  value: unknown
  options: ParameterOptionDto[] | null
  validation: ParameterValidationDto | null
  status: ParameterStatus
  requires_confirmation: boolean
}

export interface SubmitInputPayload {
  parameter: string
  value: unknown
  unit?: string
}
