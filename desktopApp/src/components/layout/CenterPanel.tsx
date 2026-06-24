import { useMemo } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { TaskErrorList } from '@/components/errors/TaskErrorList'
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
