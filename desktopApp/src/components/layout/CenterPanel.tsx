import { useMemo, useRef, useState, type MouseEvent } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { SidePanelContextMenu } from '@/components/layout/SidePanelContextMenu'
import { TaskErrorList } from '@/components/errors/TaskErrorList'
import { getWorkflowAsk } from '@/components/workflow/buildWorkflowHistory'
import { buildCenterPanelTranscript } from '@/utils/buildCenterPanelTranscript'
import { TaskCompletionNextSteps } from '@/components/workflow/TaskCompletionNextSteps'
import { WorkflowComposer } from '@/components/workflow/WorkflowComposer'
import { WorkflowHeader } from '@/components/workflow/WorkflowHeader'
import { WorkflowHistory } from '@/components/workflow/WorkflowHistory'
import '@/components/workflow/WorkflowPanel.css'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useChatStore } from '@/store/chatStore'
import { isTaskCompleted } from '@/store/taskStateManager'
import { useTaskStore } from '@/store/taskStore'
import { getSelectedText, isSelectionAskAiEligible } from '@/utils/centerPanelSelection'

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

  const workflowAsk = useMemo(() => {
    if (!activeTaskState) {
      return { kind: 'none' as const, prompt: null, parameter: null }
    }
    return getWorkflowAsk(activeTaskState, viewModel?.timeline ?? [])
  }, [activeTaskState, viewModel?.timeline])

  const historyItems = useMemo(() => {
    if (!viewModel) {
      return []
    }
    return buildCenterPanelTranscript(
      activeTaskState?.display_outputs ?? [],
      activeTaskState?.flow_guidance?.transcript_blocks ?? [],
      activeTaskState?.workflow_id,
    )
  }, [
    viewModel,
    activeTaskState?.display_outputs,
    activeTaskState?.flow_guidance?.transcript_blocks,
    activeTaskState?.workflow_id,
  ])

  const showCompletionNextSteps = isTaskCompleted(activeTaskState) && workflowAsk.kind === 'none'

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

  const workflowTitle =
    activeTaskState?.workflow_display?.display_title?.trim() ||
    activeTask.name ||
    activeTaskState?.workflow_id?.replace(/_/g, ' ') ||
    'Workflow'
  const workflowSubtitle = activeTaskState?.workflow_display?.subtitle?.trim() || null

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
        taskName={workflowTitle}
        subtitle={workflowSubtitle}
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
            ask={workflowAsk}
            disabled={!viewModel || (loading && !activeTaskState)}
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
