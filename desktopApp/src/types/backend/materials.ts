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
