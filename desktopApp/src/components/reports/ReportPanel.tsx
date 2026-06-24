import { useEffect } from 'react'

import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { useReportStore } from '@/store/reportStore'

import './ReportPanel.css'

interface ReportPanelProps {
  taskId: string
}

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
  const preview = useReportStore((state) => state.preview)
  const previewFormat = useReportStore((state) => state.previewFormat)
  const loading = useReportStore((state) => state.loading)
  const generating = useReportStore((state) => state.generating)
  const userError = useReportStore((state) => state.userError)
  const loadReport = useReportStore((state) => state.loadReport)
  const generateReport = useReportStore((state) => state.generateReport)
  const loadPreview = useReportStore((state) => state.loadPreview)
  const downloadReport = useReportStore((state) => state.downloadReport)
  const clearReport = useReportStore((state) => state.clearReport)

  useEffect(() => {
    void loadReport(taskId)
    return () => {
      clearReport()
    }
  }, [clearReport, loadReport, taskId])

  const busy = loading || generating
  const availableFormats = [
    { id: 'html', label: 'HTML', available: summary?.files?.html?.available },
    { id: 'markdown', label: 'Markdown', available: summary?.files?.markdown?.available },
    { id: 'pdf', label: 'PDF', available: summary?.files?.pdf?.available },
    { id: 'json', label: 'JSON', available: summary?.files?.json?.available },
  ]

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
            {summary.generated ? (
              <span className="report-panel__badge report-panel__badge--neutral">Generated</span>
            ) : (
              <span className="report-panel__badge report-panel__badge--neutral">Not generated</span>
            )}
          </div>
          {summary.generated && summary.conclusion ? (
            <p className="report-panel__meta">{summary.conclusion}</p>
          ) : null}
        </>
      ) : (
        <p className="report-panel__meta">Loading report status…</p>
      )}

      <div className="report-panel__actions">
        <button
          type="button"
          className="report-panel__button report-panel__button--primary"
          disabled={busy}
          onClick={() => void generateReport(taskId, 'html')}
        >
          {generating ? 'Generating…' : 'Generate report'}
        </button>
        <button
          type="button"
          className="report-panel__button"
          disabled={busy || !summary?.generated}
          onClick={() => void loadPreview(taskId, 'html')}
        >
          Preview HTML
        </button>
        <button
          type="button"
          className="report-panel__button"
          disabled={busy || !summary?.generated}
          onClick={() => void loadPreview(taskId, 'markdown')}
        >
          Preview Markdown
        </button>
      </div>

      {summary?.generated ? (
        <ul className="report-panel__files">
          {availableFormats
            .filter((item) => item.available)
            .map((item) => (
              <li key={item.id}>
                {item.label}{' '}
                <button
                  type="button"
                  className="report-panel__button"
                  disabled={busy}
                  onClick={() => void downloadReport(taskId, item.id)}
                >
                  Export
                </button>
              </li>
            ))}
        </ul>
      ) : null}

      {preview ? (
        <div className="report-panel__preview">
          {previewFormat === 'html' ? (
            <iframe
              className="report-panel__iframe"
              title="Engineering report preview"
              sandbox="allow-same-origin"
              srcDoc={preview.content}
            />
          ) : (
            <pre className="report-panel__markdown">{preview.content}</pre>
          )}
        </div>
      ) : null}
    </section>
  )
}
