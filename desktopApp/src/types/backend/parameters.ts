import type { NodeProvenanceDto } from '@/types/backend/api'

export type ParameterType =
  | 'number'
  | 'text'
  | 'dropdown'
  | 'multi_select'
  | 'checkbox'
  | 'material'
  | 'unit'
  | 'resolution_branch'

export type ParameterStatus = 'pending' | 'confirmation_required' | 'confirmed'

export interface ParameterOptionDto {
  value: string
  label: string
}

export interface ResolutionBranchComposerDto {
  type: string
  units?: string[]
  default_unit?: string
  options?: ParameterOptionDto[]
  validation?: ParameterValidationDto | null
}

export interface ResolutionBranchDto {
  id: string
  label: string
  composer: ResolutionBranchComposerDto
  submit_parameter?: string | null
}

export interface ResolutionUiDto {
  branches: ResolutionBranchDto[]
  active_branch: string | null
  default_value?: string | null
  branch_fact_key: string
}

/** @deprecated Use resolution_ui on resolution_branch parameters */
export interface DiameterUiDto {
  input_modes: ParameterOptionDto[]
  related_options: Record<string, ParameterOptionDto[]>
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
  guidance?: string | null
  editing?: boolean
  submittable?: boolean
  provenance?: NodeProvenanceDto
  resolution_ui?: ResolutionUiDto
  /** @deprecated Use resolution_ui */
  diameter_ui?: DiameterUiDto
}

export interface SubmitInputPayload {
  parameter: string
  value: unknown
  unit?: string
}
