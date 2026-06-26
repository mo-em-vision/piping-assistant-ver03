import { useEffect, useState } from 'react'

import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { useReportStore } from '@/store/reportStore'

import './TaskCompletionNextSteps.css'
import './WorkflowPanel.css'

interface TaskCompletionNextStepsProps {
  taskId: string
}

export function TaskCompletionNextSteps({ taskId }: TaskCompletionNextStepsProps) {
  const summary = useReportStore((state) => state.summary)
  const reportLoading = useReportStore((state) => state.loading)
  const generating = useReportStore((state) => state.generating)
  const reportError = useReportStore((state) => state.userError)
  const loadReport = useReportStore((state) => state.loadReport)
  const generateReport = useReportStore((state) => state.generateReport)
  const downloadReport = useReportStore((state) => state.downloadReport)
  const clearReport = useReportStore((state) => state.clearReport)

  const [expanded, setExpanded] = useState(true)

  const reportBusy = reportLoading || generating
  const generated = summary?.generated ?? false
  const htmlAvailable = summary?.files?.html?.available ?? false
  const pdfAvailable = summary?.files?.pdf?.available ?? false

  useEffect(() => {
    void loadReport(taskId)
    return () => {
      clearReport()
    }
  }, [clearReport, loadReport, taskId])

  return (
    <div
      className={`completion-next-steps workflow-panel__composer${expanded ? '' : ' completion-next-steps--collapsed'}`}
    >
      <div className="completion-next-steps__toolbar">
        <p className="workflow-panel__next-step-heading">
          <strong>Next Steps:</strong>
        </p>
        <button
          type="button"
          className="completion-next-steps__toggle"
          aria-expanded={expanded}
          aria-controls="completion-next-steps-content"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Hide' : 'Show'}
        </button>
      </div>

      {expanded ? (
        <div id="completion-next-steps-content" className="completion-next-steps__content">
          {reportError ? (
            <ErrorBanner
              error={reportError}
              onRetry={() => {
                void loadReport(taskId)
              }}
            />
          ) : null}

          <div className="completion-next-steps__actions">
            <button
              type="button"
              className="completion-next-steps__button completion-next-steps__button--primary"
              disabled={reportBusy}
              onClick={() => void generateReport(taskId)}
            >
              {generating ? 'Generating…' : 'Generate report'}
            </button>

            {generated ? (
              <>
                <button
                  type="button"
                  className="completion-next-steps__button"
                  disabled={reportBusy || !htmlAvailable}
                  onClick={() => void downloadReport(taskId, 'html')}
                >
                  Download HTML
                </button>
                <button
                  type="button"
                  className="completion-next-steps__button"
                  disabled={reportBusy || !pdfAvailable}
                  onClick={() => void downloadReport(taskId, 'pdf')}
                >
                  Download PDF
                </button>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
