export type ReportFileInfo = {
  available: boolean
  filename: string | null
  updated_at: string | null
  path?: string | null
}

export type ReportSummaryDto = {
  task_id: string
  title: string
  status: string
  conclusion: string
  missing_inputs: string[]
  formula_display?: string | null
  files: Record<string, ReportFileInfo>
  generated: boolean
  workflow_id?: string
  task_status?: string
  generation_status?: string
  with_ai?: boolean
  selected_format?: string
  draft_path?: string
}

export type ReportPreviewDto = {
  task_id: string
  format: 'html' | 'markdown'
  content: string
  filename: string
}

export type GenerateReportPayload = {
  format?: string
  with_ai?: boolean
  draft?: boolean
}
