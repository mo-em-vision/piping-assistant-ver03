import { useEffect, useState } from 'react'

import type { DevOperationDto } from '@/types/backend/inspection'

import { useOperationTracker } from './useOperationTracker'

import './InspectorPanels.css'

function formatMs(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '—'
  }
  if (value < 1000) {
    return `${value.toFixed(1)} ms`
  }
  return `${(value / 1000).toFixed(2)} s`
}

function categoryLabel(category: string): string {
  switch (category) {
    case 'http':
      return 'HTTP'
    case 'planning':
      return 'Planning'
    case 'execution':
      return 'Execution'
    case 'bootstrap':
      return 'Bootstrap'
    case 'inspection':
      return 'Inspection'
    default:
      return category
  }
}

function liveElapsedMs(operation: DevOperationDto, nowMs: number): number {
  if (operation.elapsed_ms != null && operation.started_at_epoch_ms == null) {
    return operation.elapsed_ms
  }
  if (operation.started_at_epoch_ms != null) {
    return Math.max(0, nowMs - operation.started_at_epoch_ms)
  }
  return operation.elapsed_ms ?? 0
}

function OperationRow({
  operation,
  live = false,
  nowMs,
}: {
  operation: DevOperationDto
  live?: boolean
  nowMs: number
}) {
  const duration = live ? liveElapsedMs(operation, nowMs) : operation.duration_ms
  const statusClass =
    operation.status === 'failed'
      ? 'inspector-op-row--failed'
      : live
        ? 'inspector-op-row--running'
        : 'inspector-op-row--done'

  return (
    <li className={`inspector-op-row ${statusClass}`}>
      <div className="inspector-op-row__head">
        <span className="inspector-op-row__category">{categoryLabel(operation.category)}</span>
        <span className="inspector-op-row__duration">{formatMs(duration)}</span>
      </div>
      <div className="inspector-op-row__name">{operation.name}</div>
      {operation.metadata?.task_id ? (
        <div className="inspector-op-row__meta">task: {String(operation.metadata.task_id)}</div>
      ) : null}
      {operation.error ? <div className="inspector-op-row__error">{operation.error}</div> : null}
    </li>
  )
}

export function OperationTrackerPanel() {
  const { snapshot, error, loading } = useOperationTracker()
  const [nowMs, setNowMs] = useState(() => Date.now())

  useEffect(() => {
    if (!snapshot.running.length) {
      return
    }
    const timer = window.setInterval(() => {
      setNowMs(Date.now())
    }, 200)
    return () => {
      window.clearInterval(timer)
    }
  }, [snapshot.running.length])

  return (
    <div className="inspector-operation-tracker">
      <div className="inspector-operation-tracker__header">
        <h3 className="inspector-workflow-status__title">Running operations</h3>
        {loading ? <span className="inspector-operation-tracker__status">Refreshing…</span> : null}
      </div>

      {error ? <p className="inspector-empty inspector-operation-tracker__error">{error}</p> : null}

      {!error && snapshot.running.length === 0 ? (
        <p className="inspector-empty inspector-operation-tracker__idle">No active backend work.</p>
      ) : (
        <ul className="inspector-op-list">
          {snapshot.running.map((operation) => (
            <OperationRow key={operation.id} operation={operation} live nowMs={nowMs} />
          ))}
        </ul>
      )}

      <h3 className="inspector-workflow-status__title inspector-operation-tracker__recent-title">
        Recent ({snapshot.recent.length})
      </h3>
      {!snapshot.recent.length ? (
        <p className="inspector-empty">Completed operations will appear here.</p>
      ) : (
        <ul className="inspector-op-list inspector-op-list--recent">
          {snapshot.recent.slice(0, 20).map((operation) => (
            <OperationRow
              key={`${operation.id}-${operation.finished_at ?? ''}`}
              operation={operation}
              nowMs={nowMs}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
