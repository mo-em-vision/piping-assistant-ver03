import { useTaskStore } from '@/store/taskStore'

import { SummarySection, TaskStateDevPanel } from './TaskStateDevPanel'
import { useInspectionPayload } from './useInspectionPayload'

export function TaskStateDevTab() {
  const { payload, error, loading } = useInspectionPayload()
  const activeTaskState = useTaskStore((state) => state.activeTaskState)

  if (loading && !payload && !activeTaskState) {
    return <p className="inspector-empty">Loading task state…</p>
  }

  if (!payload && !activeTaskState) {
    return (
      <p className="inspector-empty">
        {error ? 'Task state inspection requires DEV_INSPECTION_ENABLED=1 on the backend.' : 'No active task.'}
      </p>
    )
  }

  if (!payload) {
    const summary = activeTaskState?.inspector_summary
    if (summary) {
      return <SummarySection summary={summary} />
    }
    return (
      <div className="inspector-workflow-status">
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Backend task state</h3>
          <pre className="inspector-code inspector-code--tall">{JSON.stringify(activeTaskState, null, 2)}</pre>
        </section>
      </div>
    )
  }

  return <TaskStateDevPanel payload={payload} activeTaskState={activeTaskState} />
}
