import { useMemo, useRef, useState, type MouseEvent } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { SidePanelContextMenu } from '@/components/layout/SidePanelContextMenu'
import { TaskErrorList } from '@/components/errors/TaskErrorList'
import {
  buildWorkflowHistory,
  getCurrentEditableParameter,
} from '@/components/workflow/buildWorkflowHistory'
import { TaskCompletionNextSteps } from '@/components/workflow/TaskCompletionNextSteps'
import { WorkflowComposer } from '@/components/workflow/WorkflowComposer'
import { WorkflowHeader } from '@/components/workflow/WorkflowHeader'
import { WorkflowHistory } from '@/components/workflow/WorkflowHistory'
import { getNextStepPrompt } from '@/components/workflow/workflowReport'
import '@/components/workflow/WorkflowPanel.css'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useChatStore } from '@/store/chatStore'
import { isTaskCompleted } from '@/store/taskStateManager'
import { useTaskStore } from '@/store/taskStore'
import { getSelectedText, isSelectionAskAiEligible } from '@/utils/centerPanelSelection'
import { activeContextToProvenance } from '@/utils/nodeProvenance'

import './CenterPanel.css'

type AskAiMenuState = {
  x: number
  y: number
  selectedText: string
}

export function CenterPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)
  const loading = useTaskStore((state) => state.loading)
  const userError = useTaskStore((state) => state.userError)
  const refreshActiveTask = useTaskStore((state) => state.refreshActiveTask)
  const deleteTask = useTaskStore((state) => state.deleteTask)
  const askAboutSelection = useChatStore((state) => state.askAboutSelection)
  const viewModel = useActiveTaskViewModel()
  const panelRef = useRef<HTMLElement>(null)
  const [askAiMenu, setAskAiMenu] = useState<AskAiMenuState | null>(null)

  const currentParameter = useMemo(
    () => getCurrentEditableParameter(activeTaskState),
    [activeTaskState],
  )

  const historyItems = useMemo(() => {
    if (!viewModel) {
      return []
    }
    return buildWorkflowHistory(viewModel.timeline, activeTaskState?.display_outputs ?? [])
  }, [viewModel, activeTaskState?.display_outputs])

  const nextStepPrompt = useMemo(() => {
    if (!viewModel) {
      return null
    }
    return getNextStepPrompt(viewModel.timeline, currentParameter)
  }, [viewModel, currentParameter])

  const showCompletionNextSteps = isTaskCompleted(activeTaskState) && !currentParameter
  const fallbackProvenance = useMemo(
    () => activeContextToProvenance(activeTaskState?.active_node_context),
    [activeTaskState?.active_node_context],
  )

  const handleContextMenu = (event: MouseEvent<HTMLElement>) => {
    const container = panelRef.current
    const selection = window.getSelection()
    if (!container || !isSelectionAskAiEligible(container, selection)) {
      setAskAiMenu(null)
      return
    }

    const selectedText = getSelectedText(selection)
    if (!selectedText) {
      setAskAiMenu(null)
      return
    }

    event.preventDefault()
    setAskAiMenu({
      x: event.clientX,
      y: event.clientY,
      selectedText,
    })
  }

  if (!activeTask) {
    return (
      <main className="center-panel center-panel--chat">
        <ChatPanel variant="center" />
      </main>
    )
  }

  return (
    <main
      ref={panelRef}
      className="center-panel center-panel--task"
      onContextMenu={handleContextMenu}
    >
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

      <WorkflowHeader
        taskName={activeTask.name}
        context={activeTaskState?.active_node_context}
        deleteDisabled={loading}
        onDelete={() => {
          void deleteTask(activeTask.id)
        }}
      />
      <div className="workflow-panel">
        {viewModel ? (
          <WorkflowHistory items={historyItems} />
        ) : (
          <div className="workflow-panel__history">
            <p className="workflow-panel__empty">Loading task state from backend…</p>
          </div>
        )}

        {showCompletionNextSteps ? (
          <TaskCompletionNextSteps taskId={activeTask.id} />
        ) : (
          <WorkflowComposer
            parameter={currentParameter}
            nextStepPrompt={nextStepPrompt}
            disabled={!viewModel || (loading && !activeTaskState)}
            fallbackProvenance={fallbackProvenance}
          />
        )}
      </div>

      {askAiMenu ? (
        <SidePanelContextMenu
          x={askAiMenu.x}
          y={askAiMenu.y}
          ariaLabel="Ask AI about selection"
          onClose={() => setAskAiMenu(null)}
          items={[
            {
              label: 'Ask AI',
              onClick: () => {
                void askAboutSelection(askAiMenu.selectedText)
              },
            },
          ]}
        />
      ) : null}
    </main>
  )
}
