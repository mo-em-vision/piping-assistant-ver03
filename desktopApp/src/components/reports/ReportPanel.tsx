import { useEffect } from 'react'

import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { useReportStore } from '@/store/reportStore'

import './ReportPanel.css'

interface ReportPanelProps {
  taskId: string
}

const EXPORT_FORMATS = [
  { id: 'html', label: 'HTML' },
  { id: 'pdf', label: 'PDF' },
  { id: 'markdown', label: 'Markdown' },
  { id: 'json', label: 'JSON' },
] as const

function statusClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'PASS' || normalized === 'COMPLETED') {
    return 'report-panel__badge report-panel__badge--pass'
  }
  if (normalized === 'INCOMPLETE' || normalized === 'AWAITING_INPUT') {
    return 'report-panel__badge report-panel__badge--incomplete'
  }
  if (normalized === 'INVALIDATED' || normalized === 'FAIL') {
    return 'report-panel__badge report-panel__badge--invalid'
  }
  return 'report-panel__badge report-panel__badge--neutral'
}

export function ReportPanel({ taskId }: ReportPanelProps) {
  const summary = useReportStore((state) => state.summary)
  const loading = useReportStore((state) => state.loading)
  const generating = useReportStore((state) => state.generating)
  const userError = useReportStore((state) => state.userError)
  const loadReport = useReportStore((state) => state.loadReport)
  const generateReport = useReportStore((state) => state.generateReport)
  const downloadReport = useReportStore((state) => state.downloadReport)
  const clearReport = useReportStore((state) => state.clearReport)

  useEffect(() => {
    void loadReport(taskId)
    return () => {
      clearReport()
    }
  }, [clearReport, loadReport, taskId])

  const busy = loading || generating
  const generated = summary?.generated ?? false

  return (
    <section className="report-panel">
      {userError ? (
        <ErrorBanner
          error={userError}
          onRetry={() => {
            void loadReport(taskId)
          }}
        />
      ) : null}

      {summary ? (
        <>
          <div className="report-panel__status">
            <span className={statusClass(summary.status)}>{summary.status}</span>
            {generated ? (
              <span className="report-panel__badge report-panel__badge--neutral">Generated</span>
            ) : (
              <span className="report-panel__badge report-panel__badge--neutral">Not generated</span>
            )}
          </div>
          {generated && summary.conclusion ? (
            <p className="report-panel__meta">{summary.conclusion}</p>
          ) : null}
        </>
      ) : (
        <p className="report-panel__meta">Loading report status…</p>
      )}

      <button
        type="button"
        className="report-panel__button report-panel__button--primary report-panel__button--full"
        disabled={busy}
        onClick={() => void generateReport(taskId)}
      >
        {generating ? 'Generating…' : 'Generate report'}
      </button>

      <div className="report-panel__export">
        <p className="report-panel__export-label">Export</p>
        <div className="report-panel__export-options">
          {EXPORT_FORMATS.map((format) => {
            const fileKey = format.id === 'markdown' ? 'markdown' : format.id
            const available = summary?.files?.[fileKey]?.available ?? false
            const disabled = busy || !generated || !available

            return (
              <button
                key={format.id}
                type="button"
                className="report-panel__export-button"
                disabled={disabled}
                onClick={() => void downloadReport(taskId, format.id)}
              >
                {format.label}
              </button>
            )
          })}
        </div>
      </div>
    </section>
  )
}
