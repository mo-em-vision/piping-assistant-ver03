import { backendClient } from './backendClient'
import { requestManager } from './requestManager'

import type { GenerateReportPayload, ReportPreviewDto, ReportSummaryDto } from '@/types/backend/reports'

function withSession(path: string, sessionId?: string) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return `${path}${query}`
}

export const reportApi = {
  getStatus(taskId: string, sessionId?: string) {
    return requestManager.run(`reports:status:${taskId}`, () =>
      backendClient.get<ReportSummaryDto>(withSession(`/api/v1/tasks/${taskId}/reports`, sessionId)),
    )
  },

  generate(taskId: string, payload: GenerateReportPayload, sessionId?: string) {
    return requestManager.run(`reports:generate:${taskId}:${payload.format ?? 'html'}`, () =>
      backendClient.post<ReportSummaryDto>(
        withSession(`/api/v1/tasks/${taskId}/reports`, sessionId),
        payload,
        { timeoutMs: 90_000 },
      ),
    )
  },

  preview(taskId: string, format: 'html' | 'markdown', sessionId?: string) {
    const base = `/api/v1/tasks/${taskId}/reports/preview`
    const sessionQuery = sessionId ? `session_id=${encodeURIComponent(sessionId)}&` : ''
    const query = `?${sessionQuery}format=${encodeURIComponent(format)}`
    return requestManager.run(`reports:preview:${taskId}:${format}`, () =>
      backendClient.get<ReportPreviewDto>(`${base}${query}`),
    )
  },

  downloadUrl(taskId: string, format: string, sessionId?: string) {
    const base = `${backendClient.getBaseUrl()}/api/v1/tasks/${taskId}/reports/download`
    const params = new URLSearchParams({ format })
    if (sessionId) {
      params.set('session_id', sessionId)
    }
    return `${base}?${params.toString()}`
  },

  async download(taskId: string, format: string, sessionId?: string, filename?: string) {
    const url = reportApi.downloadUrl(taskId, format, sessionId)
    const response = await fetch(url, { signal: AbortSignal.timeout(90_000) })
    if (!response.ok) {
      throw new Error(`Download failed (${response.status})`)
    }
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = filename ?? `${taskId}.${format === 'markdown' ? 'md' : format}`
    anchor.click()
    URL.revokeObjectURL(objectUrl)
  },
}
