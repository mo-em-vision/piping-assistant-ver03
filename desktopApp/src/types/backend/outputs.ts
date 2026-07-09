import type { NodeProvenanceDto } from '@/types/backend/api'

export type OutputBlockType =
  | 'text'
  | 'equation'
  | 'table'
  | 'graph'
  | 'reference'
  | 'result'
  | 'next_workflows'

export type TextVariant = 'body' | 'caption' | 'warning' | 'assumption'

export interface OutputBlockBase {
  id: string
  type: OutputBlockType
  title?: string
  provenance?: NodeProvenanceDto
  lifecycle?: 'durable' | 'preview' | 'volatile'
  display_role?: string
  display_channel?: string
  equation_node_id?: string
  source_node_id?: string
  history_eligible?: boolean
  volatile?: boolean
}

export type ReferenceLinkKind = 'node' | 'table'

export interface ReferenceChipDto {
  ref_type: 'node' | 'equation' | 'table' | 'paragraph'
  id: string
  label: string
  title?: string
  target: {
    node_id?: string
    equation_id?: string
    table_id?: string
    paragraph_id?: string
  }
}

export interface ReferenceLinkDto {
  node_id: string
  label: string
  paragraph?: string | null
  symbol?: string
  reference_kind?: ReferenceLinkKind | null
}

export type ValueProvenanceSourceType =
  | 'user_input'
  | 'equation_output'
  | 'table_lookup'
  | 'default'
  | 'unknown'

export type ValueProvenanceStatus = 'resolved' | 'pending_derived' | 'awaiting_user_input'

export interface ValueProvenanceSourceRefDto {
  node_id?: string
  equation_id?: string
  table_id?: string
  paragraph_id?: string
  parameter_id?: string
}

export interface ValueProvenanceDto {
  source_type: ValueProvenanceSourceType
  status: ValueProvenanceStatus
  label: string
  detail?: string
  source_ref?: ValueProvenanceSourceRefDto
  reference_chips?: ReferenceChipDto[]
}

export interface TextOutputBlock extends OutputBlockBase {
  type: 'text'
  content: string
  content_suffix?: string
  variant?: TextVariant
  reference_links?: ReferenceLinkDto[]
  reference_chips?: ReferenceChipDto[]
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
  value_status?: string
  definition_reference?: ReferenceLinkDto | null
  value_reference?: ReferenceLinkDto | null
  value_provenance?: ValueProvenanceDto
  reference_chips?: ReferenceChipDto[]
}

export interface EquationInputTableDto {
  columns: TableColumnDto[]
  rows: EquationInputTableRowDto[]
}

export type EquationDisplayStatus = 'evaluated' | 'blocked' | 'failed'
export type EquationDisplayLatexSource =
  | 'metadata_display_latex'
  | 'metadata_display_text'
  | 'sympy_generated'
export type EquationDisplaySourceType =
  | 'user_input'
  | 'table_lookup'
  | 'equation_output'
  | 'default'
  | 'system'

export interface EquationDisplayQuantityDto {
  symbol: string
  value: number
  unit: string
  display_value: string
}

export interface EquationDisplayInputDto {
  symbol: string
  parameter_id?: string | null
  label: string
  value?: number | null
  unit?: string | null
  display_value?: string | null
  source_type?: EquationDisplaySourceType | null
  source_ref?: string | null
}

export interface EquationDisplayTraceDto {
  equation_id: string
  node_id: string
  paragraph?: string | null
  title?: string | null
  symbolic_latex: string
  substituted_latex?: string | null
  result_latex?: string | null
  latex_source: EquationDisplayLatexSource
  result?: EquationDisplayQuantityDto | null
  inputs: EquationDisplayInputDto[]
  intermediate_values: EquationDisplayQuantityDto[]
  status: EquationDisplayStatus
}

export interface EquationOutputBlock extends OutputBlockBase {
  type: 'equation'
  content: string
  display?: string
  context_intro?: string
  context_lead?: string
  variables?: EquationVariableDto[]
  input_table?: EquationInputTableDto
  result?: EquationResultDto | null
  leading_result?: EquationResultDto | null
  nomenclature_reference?: ReferenceLinkDto | null
  reference_chips?: ReferenceChipDto[]
  equation_display_trace?: EquationDisplayTraceDto | null
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
  highlight_row?: { column: string; value: string }
  summary_text?: string
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

export interface NextWorkflowActionDto {
  type: 'start_workflow'
  workflow_id: string
}

export interface NextWorkflowSuggestionDto {
  workflow_id: string
  title: string
  description?: string
  available: boolean
  action?: NextWorkflowActionDto
}

export interface NextWorkflowsOutputBlock extends OutputBlockBase {
  type: 'next_workflows'
  content: string
  suggestions: NextWorkflowSuggestionDto[]
}

export type DisplayOutputBlock =
  | TextOutputBlock
  | EquationOutputBlock
  | TableOutputBlock
  | GraphOutputBlock
  | ReferenceOutputBlock
  | ResultOutputBlock
  | NextWorkflowsOutputBlock
