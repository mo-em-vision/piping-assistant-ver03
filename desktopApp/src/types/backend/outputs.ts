import type { NodeProvenanceDto } from '@/types/backend/api'

export type OutputBlockType = 'text' | 'equation' | 'table' | 'graph' | 'reference' | 'result'

export type TextVariant = 'body' | 'caption' | 'warning' | 'assumption'

export interface OutputBlockBase {
  id: string
  type: OutputBlockType
  title?: string
  provenance?: NodeProvenanceDto
}

export type ReferenceLinkKind = 'node' | 'table'

export interface ReferenceLinkDto {
  node_id: string
  label: string
  paragraph?: string | null
  symbol?: string
  reference_kind?: ReferenceLinkKind | null
}

export interface TextOutputBlock extends OutputBlockBase {
  type: 'text'
  content: string
  content_suffix?: string
  variant?: TextVariant
  reference_links?: ReferenceLinkDto[]
  reference_links_placement?: 'inline' | 'below'
}

export interface EquationVariableDto {
  symbol: string
  name: string
  value?: string | null
  unit?: string | null
}

export interface EquationResultDto {
  label: string
  value: string
  unit?: string
}

export interface EquationInputTableRowDto {
  symbol?: string
  definition?: string
  value?: string
  definition_reference?: ReferenceLinkDto | null
  value_reference?: ReferenceLinkDto | null
}

export interface EquationInputTableDto {
  columns: TableColumnDto[]
  rows: EquationInputTableRowDto[]
}

export interface EquationOutputBlock extends OutputBlockBase {
  type: 'equation'
  content: string
  display?: string
  variables?: EquationVariableDto[]
  input_table?: EquationInputTableDto
  result?: EquationResultDto | null
  leading_result?: EquationResultDto | null
  nomenclature_reference?: ReferenceLinkDto | null
}

export interface TableColumnDto {
  key: string
  label: string
  sortable?: boolean
}

export interface TableOutputBlock extends OutputBlockBase {
  type: 'table'
  columns: TableColumnDto[]
  rows: Array<Record<string, unknown>>
  searchable?: boolean
  compact?: boolean
}

export interface GraphPointDto {
  x: string | number
  y: number
}

export interface GraphSeriesDto {
  name: string
  points: GraphPointDto[]
}

export interface GraphOutputBlock extends OutputBlockBase {
  type: 'graph'
  chart_type: 'line' | 'bar' | 'scatter'
  x_label?: string
  y_label?: string
  series: GraphSeriesDto[]
}

export interface ReferenceOutputBlock extends OutputBlockBase {
  type: 'reference'
  standard: string
  paragraph?: string
  table?: string
  figure?: string
  excerpt?: string
  source_node?: string
}

export interface ResultOutputBlock extends OutputBlockBase {
  type: 'result'
  label: string
  value: string
  unit?: string
  status?: 'pass' | 'fail' | 'pending' | 'info'
}

export type DisplayOutputBlock =
  | TextOutputBlock
  | EquationOutputBlock
  | TableOutputBlock
  | GraphOutputBlock
  | ReferenceOutputBlock
  | ResultOutputBlock
