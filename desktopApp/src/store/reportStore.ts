import { create } from 'zustand'

import { mockReportPreview, mockReportSummary } from '@/mock/report.mock'
import { reportApi } from '@/services/api/reportApi'
import { getActiveSessionId } from '@/store/projectStore'
import { toUserFacingError } from '@/types/backend/errors'
import type { UserFacingError } from '@/types/frontend/userError'
import type { ReportPreviewDto, ReportSummaryDto } from '@/types/backend/reports'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface ReportStoreState {
  summary: ReportSummaryDto | null
  preview: ReportPreviewDto | null
  previewFormat: 'html' | 'markdown'
  loading: boolean
  generating: boolean
  userError: UserFacingError | null
  loadReport: (taskId: string) => Promise<void>
  generateReport: (taskId: string, format?: string) => Promise<void>
  loadPreview: (taskId: string, format?: 'html' | 'markdown') => Promise<void>
  downloadReport: (taskId: string, format: string) => Promise<void>
  clearReport: () => void
}

export const useReportStore = create<ReportStoreState>((set, get) => ({
  summary: useMockData ? mockReportSummary : null,
  preview: useMockData ? mockReportPreview : null,
  previewFormat: 'html',
  loading: false,
  generating: false,
  userError: null,

  loadReport: async (taskId: string) => {
    if (useMockData) {
      set({ summary: { ...mockReportSummary, task_id: taskId }, userError: null })
      return
    }

    set({ loading: true, userError: null })
    try {
      const summary = await reportApi.getStatus(taskId, getActiveSessionId())
      set({ summary, loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  generateReport: async (taskId: string, format = 'html') => {
    if (useMockData) {
      set({
        summary: {
          ...mockReportSummary,
          task_id: taskId,
          generated: true,
          generation_status: 'ready',
          files: {
            html: { available: true, filename: `${taskId}.html`, updated_at: new Date().toISOString() },
            markdown: { available: true, filename: `${taskId}.md`, updated_at: new Date().toISOString() },
            pdf: { available: true, filename: `${taskId}.pdf`, updated_at: new Date().toISOString() },
            json: { available: true, filename: `${taskId}.json`, updated_at: new Date().toISOString() },
          },
        },
        userError: null,
      })
      return
    }

    set({ generating: true, userError: null })
    try {
      const summary = await reportApi.generate(
        taskId,
        { format, with_ai: true },
        getActiveSessionId(),
      )
      set({ summary, generating: false, userError: null })
    } catch (error) {
      set({ generating: false, userError: toUserFacingError(error) })
    }
  },

  loadPreview: async (taskId: string, format: 'html' | 'markdown' = 'html') => {
    if (useMockData) {
      set({ preview: { ...mockReportPreview, task_id: taskId, format }, previewFormat: format, userError: null })
      return
    }

    set({ loading: true, userError: null })
    try {
      const preview = await reportApi.preview(taskId, format, getActiveSessionId())
      set({ preview, previewFormat: format, loading: false, userError: null })
    } catch (error) {
      set({ loading: false, userError: toUserFacingError(error) })
    }
  },

  downloadReport: async (taskId: string, format: string) => {
    if (useMockData) {
      const blob = new Blob([mockReportPreview.content], { type: 'text/html' })
      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = `${taskId}.html`
      anchor.click()
      URL.revokeObjectURL(objectUrl)
      return
    }

    const summary = get().summary
    const fileInfo = summary?.files?.[format === 'md' ? 'markdown' : format]
    await reportApi.download(taskId, format, getActiveSessionId(), fileInfo?.filename ?? undefined)
  },

  clearReport: () =>
    set({
      summary: useMockData ? mockReportSummary : null,
      preview: useMockData ? mockReportPreview : null,
      userError: null,
    }),
}))
