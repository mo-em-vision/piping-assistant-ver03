import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type PendingGroupProps = {
  title: string
  rows: Array<{
    key: string
    label: string
    meta?: string
    reason?: string | null
    waitingOn?: string[]
  }>
}

function PendingGroup({ title, rows }: PendingGroupProps) {
  if (!rows.length) {
    return null
  }

  return (
    <div className="inspector-requirements-group">
      <h4 className="inspector-requirements-group__title">{title}</h4>
      <ul className="inspector-missing-list">
        {rows.map((row) => (
          <li key={row.key}>
            <strong>{row.label}</strong>
            {row.meta ? <span className="inspector-rationale-meta"> ({row.meta})</span> : null}
            {row.reason ? <p className="inspector-timeline__reason">{row.reason}</p> : null}
            {row.waitingOn?.length ? (
              <p className="inspector-timeline__waiting">Waiting on: {row.waitingOn.join(', ')}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

type PlannerPendingWorkSectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerPendingWorkSection({ projection }: PlannerPendingWorkSectionProps) {
  const nodeRows = (projection.pending_nodes ?? []).map((row) => ({
    key: row.node_id,
    label: row.title ?? row.node_id,
    meta: row.node_type ?? undefined,
    reason: row.reason,
    waitingOn: row.waiting_on,
  }))

  const calculationRows = (projection.pending_calculations ?? []).map((row) => ({
    key: row.field,
    label: row.title,
    meta: row.status,
    reason: row.reason,
    waitingOn: row.depends_on,
  }))

  const validationRows = (projection.pending_validations ?? []).map((row) => ({
    key: row.field,
    label: row.title,
    meta: row.status,
    reason: row.reason,
  }))

  const lookupRows = (projection.pending_lookups ?? []).map((row) => ({
    key: row.field,
    label: row.title,
    meta: row.status,
    reason: row.reason,
    waitingOn: row.depends_on,
  }))

  const hasAny =
    nodeRows.length || calculationRows.length || validationRows.length || lookupRows.length

  if (!hasAny) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Pending Work</h3>
        <p className="inspector-empty">not available</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Pending Work</h3>
      <PendingGroup title="Pending nodes" rows={nodeRows} />
      <PendingGroup title="Pending calculations" rows={calculationRows} />
      <PendingGroup title="Pending validations" rows={validationRows} />
      <PendingGroup title="Pending lookups" rows={lookupRows} />
    </section>
  )
}
