/** MOCK_DATA — sample report preview for mock mode. */
import type { ReportPreviewDto, ReportSummaryDto } from '@/types/backend/reports'

export const mockReportSummary: ReportSummaryDto = {
  task_id: 'mock-pipe-thickness',
  title: 'Pipe Wall Thickness Design Report',
  status: 'INCOMPLETE',
  conclusion: 'Report preview available from collected task inputs.',
  missing_inputs: ['nominal_pipe_size'],
  formula_display: 't = PD / 2(SEW + PY)',
  generated: false,
  files: {
    html: { available: false, filename: null, updated_at: null },
    markdown: { available: false, filename: null, updated_at: null },
    pdf: { available: false, filename: null, updated_at: null },
    json: { available: false, filename: null, updated_at: null },
  },
}

export const mockReportPreview: ReportPreviewDto = {
  task_id: 'mock-pipe-thickness',
  format: 'html',
  filename: 'mock-pipe-thickness.html',
  content: `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Mock Report</title></head>
<body>
  <h1>Pipe Wall Thickness Design Report</h1>
  <p>Mock preview for desktop development mode.</p>
  <h2>Executive Summary</h2>
  <p>Design pressure 8 bar, material SA-106B. Required thickness pending final inputs.</p>
</body></html>`,
}
