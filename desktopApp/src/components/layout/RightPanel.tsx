import { useState } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ParameterEditDialog } from '@/components/engineering/ParameterEditDialog'
import { ReportPanel } from '@/components/reports/ReportPanel'
import { NodeReferenceTab } from '@/components/standards/NodeReferenceTab'
import { TableReferenceTab } from '@/components/standards/TableReferenceTab'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { isReportSectionVisible } from '@/store/taskStateManager'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { inputApi } from '@/services/api/inputApi'
import { getActiveSessionId } from '@/store/projectStore'
import { toUserFacingError } from '@/types/backend/errors'
import type { ParameterEditImpactDto } from '@/types/backend/api'
import { StatusIndicator } from '@/components/engineering/StatusIndicator'
import { TaskTimeline } from '@/components/engineering/TaskTimeline'

import { PanelSection } from './PanelSection'
import './SidePanel.css'

function TaskContextTab() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)
  const sessionId = useTaskStore((state) => state.sessionId)
  const applyTaskState = useTaskStore((state) => state.applyTaskState)
  const viewModel = useActiveTaskViewModel()
  const [pendingEdit, setPendingEdit] = useState<{
    stepId: string
    title: string
    impact: ParameterEditImpactDto
  } | null>(null)
  const [editBusy, setEditBusy] = useState(false)

  const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

  const confirmParameterEdit = async (stepId: string) => {
    if (!activeTask || useMockData) {
      return
    }
    setEditBusy(true)
    try {
      const state = await inputApi.beginEdit(
        activeTask.id,
        stepId,
        sessionId ?? getActiveSessionId(),
      )
      applyTaskState(state)
      setPendingEdit(null)
    } catch (error) {
      useTaskStore.setState({ userError: toUserFacingError(error) })
    } finally {
      setEditBusy(false)
    }
  }

  const handleEditStep = async (stepId: string) => {
    if (!activeTask || useMockData) {
      return
    }
    const step = viewModel?.timeline.find((item) => item.id === stepId)
    if (!step) {
      return
    }

    setEditBusy(true)
    try {
      const impact = await inputApi.previewEdit(
        activeTask.id,
        stepId,
        sessionId ?? getActiveSessionId(),
      )
      if (impact.affects_design) {
        setPendingEdit({ stepId, title: step.title, impact })
        return
      }
      await confirmParameterEdit(stepId)
    } catch (error) {
      useTaskStore.setState({ userError: toUserFacingError(error) })
    } finally {
      setEditBusy(false)
    }
  }

  if (!activeTask) {
    return null
  }

  return (
    <div className="side-panel__tab-body">
      <ParameterEditDialog
        impact={pendingEdit?.impact ?? null}
        stepTitle={pendingEdit?.title ?? ''}
        busy={editBusy}
        onConfirm={() => {
          if (pendingEdit) {
            void confirmParameterEdit(pendingEdit.stepId)
          }
        }}
        onCancel={() => setPendingEdit(null)}
      />
      <PanelSection title="Task state">
        {viewModel ? (
          <>
            <div className="task-state-summary">
              <StatusIndicator label={viewModel.statusLabel} variant={viewModel.statusVariant} />
            </div>
            <TaskTimeline steps={viewModel.timeline} onEditStep={handleEditStep} />
          </>
        ) : (
          <p className="side-panel__hint">Task progress will load from the backend.</p>
        )}
      </PanelSection>

      {viewModel && isReportSectionVisible(viewModel.timeline) ? (
        <PanelSection title="Engineering report">
          <ReportPanel taskId={activeTask.id} />
        </PanelSection>
      ) : null}
    </div>
  )
}

function ChatTab() {
  const activeTask = useTaskStore((state) => state.activeTask)

  if (!activeTask) {
    return null
  }

  return (
    <div className="side-panel__tab-body side-panel__tab-body--chat">
      <ChatPanel variant="sidebar" taskId={activeTask.id} />
    </div>
  )
}

export function RightPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const tabs = useRightPanelStore((state) => state.tabs)
  const activeTabId = useRightPanelStore((state) => state.activeTabId)
  const setActiveTab = useRightPanelStore((state) => state.setActiveTab)
  const closeTab = useRightPanelStore((state) => state.closeTab)
  const toggleRightCollapsed = useUiStore((state) => state.toggleRightCollapsed)

  if (!activeTask) {
    return null
  }

  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]

  return (
    <aside className="side-panel side-panel--right">
      <header className="side-panel__header">
        <div className="side-panel__tab-bar" role="tablist" aria-label="Right panel tabs">
          {tabs.map((tab) => {
            const isActive = tab.id === activeTabId
            const isClosable = tab.kind === 'reference'

            return (
              <div
                key={tab.id}
                className={`side-panel__tab-item${isActive ? ' side-panel__tab-item--active' : ''}${isClosable ? ' side-panel__tab-item--closable' : ''}`}
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className="side-panel__tab"
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="side-panel__tab-label">{tab.title}</span>
                </button>
                {isClosable ? (
                  <button
                    type="button"
                    className="side-panel__tab-close"
                    aria-label={`Close ${tab.title}`}
                    onClick={(event) => {
                      event.stopPropagation()
                      closeTab(tab.id)
                    }}
                  >
                    ×
                  </button>
                ) : null}
              </div>
            )
          })}
        </div>
        <button
          type="button"
          className="side-panel__collapse"
          onClick={toggleRightCollapsed}
          aria-label="Collapse right panel"
          title="Collapse panel"
        >
          ›
        </button>
      </header>

      <div className="side-panel__content side-panel__content--tabs">
        {activeTab.kind === 'task' ? <TaskContextTab /> : null}
        {activeTab.kind === 'chat' ? <ChatTab /> : null}
        {activeTab.kind === 'reference' ? (
          <div className="side-panel__tab-body side-panel__tab-body--reference">
            {activeTab.referenceKind === 'table' ? (
              <TableReferenceTab
                tableId={activeTab.referenceId}
                viewerContext={activeTab.viewerContext}
              />
            ) : (
              <NodeReferenceTab nodeId={activeTab.referenceId} />
            )}
          </div>
        ) : null}
      </div>
    </aside>
  )
}
