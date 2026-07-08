import { useLayoutEffect, useRef, useState, lazy, Suspense } from 'react'

import { ChatPanel } from '@/components/chat/ChatPanel'
import { ParameterEditDialog } from '@/components/engineering/ParameterEditDialog'
import { ReportPanel } from '@/components/reports/ReportPanel'
import { MaterialReferenceTab } from '@/components/standards/MaterialReferenceTab'
import { NodeReferenceTab } from '@/components/standards/NodeReferenceTab'
import { StandardsBrowserTab } from '@/components/standards/StandardsBrowserTab'
import { TableReferenceTab } from '@/components/standards/TableReferenceTab'
import { env } from '@/config/env'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useDevUiActive } from '@/hooks/useDevUiActive'
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

import { ChatTabIcon, pinnedTabAriaLabel, StandardsTabIcon, TaskTabIcon } from './RightPanelTabIcon'
import { PanelSection } from './PanelSection'
import './SidePanel.css'

const PlannerDevTab = env.devToolsAvailable
  ? lazy(async () => {
      const module = await import('@dev-ui/inspector/PlannerDevTab')
      return { default: module.PlannerDevTab }
    })
  : null

const TaskStateDevTab = env.devToolsAvailable
  ? lazy(async () => {
      const module = await import('@dev-ui/inspector/TaskStateDevTab')
      return { default: module.TaskStateDevTab }
    })
  : null

const PerformanceDevTab = env.devToolsAvailable
  ? lazy(async () => {
      const module = await import('@dev-ui/inspector/PerformanceDevTab')
      return { default: module.PerformanceDevTab }
    })
  : null

const TAB_SCROLL_INTO_VIEW_OPTIONS: ScrollIntoViewOptions = {
  block: 'nearest',
  inline: 'nearest',
}

function scrollTabItemIntoView(element: HTMLElement | null) {
  element?.scrollIntoView(TAB_SCROLL_INTO_VIEW_OPTIONS)
}

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

      {viewModel && isReportSectionVisible(viewModel.timeline, activeTaskState) ? (
        <PanelSection title="Engineering report">
          <ReportPanel taskId={activeTask.id} />
        </PanelSection>
      ) : null}
    </div>
  )
}

function ChatTab() {
  const activeTask = useTaskStore((state) => state.activeTask)

  return (
    <div className="side-panel__tab-body side-panel__tab-body--chat">
      <ChatPanel variant="sidebar" taskId={activeTask?.id} />
    </div>
  )
}

export function RightPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const viewModel = useActiveTaskViewModel()
  const devUiActive = useDevUiActive()
  const tabs = useRightPanelStore((state) => state.tabs)
  const activeTabId = useRightPanelStore((state) => state.activeTabId)
  const setActiveTab = useRightPanelStore((state) => state.setActiveTab)
  const closeTab = useRightPanelStore((state) => state.closeTab)
  const toggleRightCollapsed = useUiStore((state) => state.toggleRightCollapsed)
  const tabItemRefs = useRef(new Map<string, HTMLDivElement>())
  const tabIdsKey = tabs.map((tab) => tab.id).join('|')

  useLayoutEffect(() => {
    const activeTabElement = tabItemRefs.current.get(activeTabId)
    scrollTabItemIntoView(activeTabElement ?? null)
  }, [activeTabId, tabIdsKey])

  const visibleTabs = tabs.filter((tab) => {
    if (tab.kind === 'task' || tab.kind === 'planner' || tab.kind === 'dev-task-state') {
      return Boolean(activeTask)
    }
    if (tab.kind === 'dev-performance') {
      return devUiActive
    }
    return true
  })
  const activeTab = visibleTabs.find((tab) => tab.id === activeTabId) ?? visibleTabs[0]

  const setTabItemRef = (tabId: string, element: HTMLDivElement | null) => {
    if (element) {
      tabItemRefs.current.set(tabId, element)
      return
    }
    tabItemRefs.current.delete(tabId)
  }

  return (
    <aside className="side-panel side-panel--right">
      <header className="side-panel__header">
        <div
          className="side-panel__tab-bar"
          role="tablist"
          aria-label="Right panel tabs"
        >
          {visibleTabs.map((tab) => {
            const isActive = tab.id === activeTabId
            const isClosable = tab.kind === 'reference' || tab.kind === 'material'
            const isIconOnly =
              tab.kind === 'task' || tab.kind === 'chat' || tab.kind === 'standards'
            const tabAriaLabel =
              tab.kind === 'task'
                ? pinnedTabAriaLabel('task', viewModel?.statusLabel)
                : tab.kind === 'chat'
                  ? pinnedTabAriaLabel('chat')
                  : tab.kind === 'standards'
                    ? pinnedTabAriaLabel('standards')
                    : tab.kind === 'planner'
                      ? 'Planner'
                      : tab.kind === 'dev-task-state'
                        ? 'Task State'
                        : tab.kind === 'dev-performance'
                          ? 'Performance'
                          : undefined
            const isDevTab =
              tab.kind === 'planner' || tab.kind === 'dev-task-state' || tab.kind === 'dev-performance'

            return (
              <div
                key={tab.id}
                ref={(element) => setTabItemRef(tab.id, element)}
                className={`side-panel__tab-item${isActive ? ' side-panel__tab-item--active' : ''}${isClosable ? ' side-panel__tab-item--closable' : ''}${isDevTab ? ' side-panel__tab-item--dev' : ''}`}
                onMouseEnter={
                  isClosable
                    ? (event) => scrollTabItemIntoView(event.currentTarget)
                    : undefined
                }
                onFocus={
                  isClosable
                    ? (event) => scrollTabItemIntoView(event.currentTarget)
                    : undefined
                }
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-label={tabAriaLabel}
                  title={tabAriaLabel}
                  className={`side-panel__tab${isIconOnly ? ' side-panel__tab--icon-only' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.kind === 'task' ? (
                    <TaskTabIcon variant={viewModel?.statusVariant ?? 'neutral'} />
                  ) : tab.kind === 'chat' ? (
                    <ChatTabIcon />
                  ) : tab.kind === 'standards' ? (
                    <StandardsTabIcon />
                  ) : (
                    <span className="side-panel__tab-label">{tab.title}</span>
                  )}
                </button>
                {isClosable ? (
                  <button
                    type="button"
                    className="side-panel__tab-close"
                    aria-label={`Close ${tab.title}`}
                    onFocus={(event) => scrollTabItemIntoView(event.currentTarget.parentElement)}
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
        {activeTab?.kind === 'task' ? <TaskContextTab /> : null}
        {devUiActive && activeTab?.kind === 'planner' && PlannerDevTab ? (
          <div className="side-panel__tab-body side-panel__tab-body--dev">
            <Suspense fallback={<p className="side-panel__hint">Loading planner…</p>}>
              <PlannerDevTab />
            </Suspense>
          </div>
        ) : null}
        {devUiActive && activeTab?.kind === 'dev-task-state' && TaskStateDevTab ? (
          <div className="side-panel__tab-body side-panel__tab-body--dev">
            <Suspense fallback={<p className="side-panel__hint">Loading task state…</p>}>
              <TaskStateDevTab />
            </Suspense>
          </div>
        ) : null}
        {devUiActive && activeTab?.kind === 'dev-performance' && PerformanceDevTab ? (
          <Suspense fallback={<p className="side-panel__hint">Loading performance…</p>}>
            <PerformanceDevTab />
          </Suspense>
        ) : null}
        {activeTab?.kind === 'chat' ? <ChatTab /> : null}
        {activeTab?.kind === 'standards' ? (
          <div className="side-panel__tab-body side-panel__tab-body--standards">
            <StandardsBrowserTab />
          </div>
        ) : null}
        {activeTab?.kind === 'reference' ? (
          <div className="side-panel__tab-body side-panel__tab-body--reference">
            {activeTab.referenceKind === 'table' ? (
              <TableReferenceTab
                tableId={activeTab.referenceId}
                viewerContext={activeTab.viewerContext}
              />
            ) : (
              <NodeReferenceTab
                nodeId={activeTab.referenceId}
                subsectionId={
                  activeTab.viewerContext && 'subsectionId' in activeTab.viewerContext
                    ? activeTab.viewerContext.subsectionId
                    : undefined
                }
              />
            )}
          </div>
        ) : null}
        {activeTab?.kind === 'material' ? (
          <div className="side-panel__tab-body side-panel__tab-body--reference">
            <MaterialReferenceTab materialId={activeTab.materialId} />
          </div>
        ) : null}
      </div>
    </aside>
  )
}
