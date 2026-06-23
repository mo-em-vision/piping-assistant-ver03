import { useMemo } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { TaskErrorList } from '@/components/errors/TaskErrorList'
import { StatusIndicator } from '@/components/engineering/StatusIndicator'
import {
  buildWorkflowHistory,
  getCurrentEditableParameter,
} from '@/components/workflow/buildWorkflowHistory'
import { WorkflowComposer } from '@/components/workflow/WorkflowComposer'
import { WorkflowHistory } from '@/components/workflow/WorkflowHistory'
import '@/components/workflow/WorkflowPanel.css'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useTaskStore } from '@/store/taskStore'

import './CenterPanel.css'

export function CenterPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const refreshActiveTask = useTaskStore((state) => state.refreshActiveTask)
  const clearActiveTask = useTaskStore((state) => state.clearActiveTask)
  const viewModel = useActiveTaskViewModel()

  const historyItems = useMemo(() => {
    if (!viewModel) {
      return []
    }
    return buildWorkflowHistory(
      viewModel.timeline,
      activeTaskState?.display_outputs ?? [],
      activeTaskState?.inputs ?? {},
      activeTaskState?.parameters ?? [],
    )
  }, [viewModel, activeTaskState?.display_outputs, activeTaskState?.inputs, activeTaskState?.parameters])

  const currentParameter = useMemo(
    () => getCurrentEditableParameter(activeTaskState),
    [activeTaskState],
  )

  if (!activeTask) {
    return (
      <main className="center-panel center-panel--chat">
        <ChatPanel variant="center" />
      </main>
    )
  }

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

      {activeTaskState?.errors?.length ? (
        <div className="center-panel__errors">
          <TaskErrorList
            errors={activeTaskState.errors}
            onRefresh={() => {
              void refreshActiveTask()
            }}
          />
        </div>
      ) : null}

      {userError ? (
        <div className="center-panel__banner">
          <ErrorBanner
            error={userError}
            onRetry={() => {
              void refreshActiveTask()
            }}
          />
        </div>
      ) : null}

      <div className="workflow-panel">
        {viewModel ? (
          <WorkflowHistory items={historyItems} />
        ) : (
          <div className="workflow-panel__history">
            <p className="workflow-panel__empty">Loading task state from backend…</p>
          </div>
        )}

        <WorkflowComposer
          parameter={currentParameter}
          guidance={viewModel?.currentStep?.hint ?? null}
          disabled={loading || !viewModel}
        />
      </div>
    </main>
  )
}
