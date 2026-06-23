export type OutputBlockType = 'text' | 'equation' | 'table' | 'graph' | 'reference' | 'result'

export type TextVariant = 'body' | 'caption' | 'warning'

export interface OutputBlockBase {
  id: string
  type: OutputBlockType
  title?: string
}

export interface TextOutputBlock extends OutputBlockBase {
  type: 'text'
  content: string
  variant?: TextVariant
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

export interface EquationOutputBlock extends OutputBlockBase {
  type: 'equation'
  content: string
  display?: string
  variables?: EquationVariableDto[]
  result?: EquationResultDto | null
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
