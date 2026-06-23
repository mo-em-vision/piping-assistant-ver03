import { ChatPanel } from '@/components/chat/ChatPanel'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { TaskErrorList } from '@/components/errors/TaskErrorList'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { ParameterForm } from '@/components/inputs/ParameterForm'
import { OutputRenderer } from '@/components/outputs/OutputRenderer'
import { ReportPanel } from '@/components/reports/ReportPanel'
import { useTaskStore } from '@/store/taskStore'
import { StatusIndicator } from '@/components/engineering/StatusIndicator'
import { TaskTimeline } from '@/components/engineering/TaskTimeline'

import './CenterPanel.css'

export function CenterPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const refreshActiveTask = useTaskStore((state) => state.refreshActiveTask)
  const clearActiveTask = useTaskStore((state) => state.clearActiveTask)
  const viewModel = useActiveTaskViewModel()

  if (!activeTask) {
    return (
      <main className="center-panel center-panel--chat">
        <ChatPanel variant="center" />
      </main>
    )
  }

  const collectedInputs = activeTaskState
    ? Object.entries(activeTaskState.inputs).filter(([, input]) => {
        const record = input as { display_value?: string; value?: unknown }
        return record.display_value != null || record.value != null
      })
    : []

  return (
    <main className="center-panel center-panel--task">
      <header className="center-panel__header center-panel__header--task">
        <div>
          <p className="center-panel__eyebrow">{activeTask.discipline}</p>
          <h2 className="center-panel__title">{activeTask.name}</h2>
          <p className="center-panel__subtitle">{activeTask.description}</p>
          {viewModel ? (
            <div className="center-panel__status-row">
              <StatusIndicator label={viewModel.statusLabel} variant={viewModel.statusVariant} />
            </div>
          ) : null}
        </div>
        <button type="button" className="center-panel__close" onClick={clearActiveTask} disabled={loading}>
          Close task
        </button>
      </header>

      <div className="center-panel__workspace">
        <TaskErrorList
          errors={activeTaskState?.errors ?? []}
          onRefresh={() => {
            void refreshActiveTask()
          }}
        />

        {userError ? (
          <ErrorBanner
            error={userError}
            onRetry={() => {
              void refreshActiveTask()
            }}
          />
        ) : null}

        <section className="workspace-section workspace-section--timeline">
          <h3>Workflow progress</h3>
          {viewModel ? (
            <TaskTimeline steps={viewModel.timeline} />
          ) : (
            <p className="placeholder__hint">Loading task state from backend…</p>
          )}
        </section>

        <section className="workspace-section">
          <h3>Engineering inputs</h3>
          {activeTaskState?.parameters?.length ? (
            <ParameterForm parameters={activeTaskState.parameters} />
          ) : (
            <p className="placeholder__hint">
              {viewModel?.currentStep?.hint ?? 'No parameters requested yet.'}
            </p>
          )}

          {collectedInputs.length > 0 ? (
            <>
              <h4 className="workspace-section__subheading">Collected</h4>
              <dl className="collected-inputs">
                {collectedInputs.map(([key, input]) => {
                  const record = input as { display_value?: string; value?: unknown; unit?: string }
                  const display =
                    record.display_value ??
                    (record.value != null ? String(record.value) : '') +
                      (record.unit && record.unit !== 'dimensionless' ? ` ${record.unit}` : '')
                  return (
                    <div key={key}>
                      <dt>{key.replace(/_/g, ' ')}</dt>
                      <dd>{display}</dd>
                    </div>
                  )
                })}
              </dl>
            </>
          ) : null}
        </section>

        <section className="workspace-section">
          <h3>Outputs</h3>
          <OutputRenderer blocks={activeTaskState?.display_outputs ?? []} />
        </section>

        <section className="workspace-section">
          <h3>Engineering report</h3>
          <ReportPanel taskId={activeTask.id} />
        </section>
      </div>
    </main>
  )
}
