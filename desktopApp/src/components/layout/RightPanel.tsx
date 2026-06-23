import { ChatPanel } from '@/components/chat/ChatPanel'
import { ReportPanel } from '@/components/reports/ReportPanel'
import { useActiveTaskViewModel } from '@/hooks/useActiveTaskViewModel'
import { useChatStore } from '@/store/chatStore'
import { useTaskStore } from '@/store/taskStore'
import { useUiStore } from '@/store/uiStore'
import { StatusIndicator } from '@/components/engineering/StatusIndicator'
import { TaskProgress } from '@/components/engineering/TaskProgress'
import { TaskTimeline } from '@/components/engineering/TaskTimeline'

import { PanelSection } from './PanelSection'
import './SidePanel.css'

export function RightPanel() {
  const activeTask = useTaskStore((state) => state.activeTask)
  const activeTaskState = useTaskStore((state) => state.activeTaskState)
  const viewModel = useActiveTaskViewModel()
  const lastContext = useChatStore((state) => state.lastContext)
  const toggleRightCollapsed = useUiStore((state) => state.toggleRightCollapsed)

  if (!activeTask) {
    return null
  }

  return (
    <aside className="side-panel side-panel--right">
      <header className="side-panel__header">
        <h2 className="side-panel__title">Task context</h2>
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

      <div className="side-panel__content side-panel__content--with-chat">
        <div className="side-panel__summary">
        <PanelSection title="Task state">
          {viewModel ? (
            <>
              <div className="task-state-summary">
                <StatusIndicator label={viewModel.statusLabel} variant={viewModel.statusVariant} />
                <TaskProgress
                  percent={viewModel.progressPercent}
                  completedCount={viewModel.completedCount}
                  totalCount={viewModel.totalCount}
                />
              </div>
              <TaskTimeline steps={viewModel.timeline} />
            </>
          ) : (
            <p className="side-panel__hint">Task progress will load from the backend.</p>
          )}
        </PanelSection>

        <PanelSection title="Parameters">
          <dl className="param-list">
            <div>
              <dt>Task</dt>
              <dd>{activeTask.name}</dd>
            </div>
            <div>
              <dt>Discipline</dt>
              <dd>{activeTask.discipline}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{viewModel?.statusLabel ?? activeTaskState?.status ?? activeTask.status}</dd>
            </div>
            {viewModel?.currentStep ? (
              <div>
                <dt>Current step</dt>
                <dd>{viewModel.currentStep.title}</dd>
              </div>
            ) : null}
            {activeTaskState?.active_nodes.length ? (
              <div>
                <dt>Active nodes</dt>
                <dd>{activeTaskState.active_nodes.join(', ')}</dd>
              </div>
            ) : null}
          </dl>
        </PanelSection>

        {viewModel?.warnings.length ? (
          <PanelSection title="Warnings">
            <ul className="warning-list">
              {viewModel.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </PanelSection>
        ) : null}

        <PanelSection title="Engineering report">
          <ReportPanel taskId={activeTask.id} />
        </PanelSection>
        </div>

        <PanelSection title="AI assistance" className="side-panel__chat-section">
          <ChatPanel
            variant="sidebar"
            taskId={activeTask.id}
            context={
              lastContext?.task_id
                ? lastContext
                : activeTaskState
                  ? {
                      task_id: activeTaskState.task_id,
                      workflow_id: activeTaskState.workflow_id,
                      status: activeTaskState.status,
                      current_step_id: activeTaskState.progress.current_step_id,
                      active_nodes: activeTaskState.active_nodes,
                      missing_inputs: activeTaskState.progress.missing_inputs,
                      output_count: activeTaskState.display_outputs?.length ?? 0,
                    }
                  : null
            }
          />
        </PanelSection>
      </div>
    </aside>
  )
}
