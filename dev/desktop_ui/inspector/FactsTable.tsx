import type { TaskFactRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type FactsTableProps = {
  rows: TaskFactRowDto[]
}

export function FactsTable({ rows }: FactsTableProps) {
  if (!rows.length) {
    return <p className="inspector-empty">No facts or inputs stored yet.</p>
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Facts / inputs</h3>
      <table className="inspector-table">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Source</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field}>
              <td>
                <strong>{row.label}</strong>
                {row.symbol ? <span className="inspector-rationale-meta"> ({row.symbol})</span> : null}
                <div className="inspector-rationale-meta">{row.field}</div>
              </td>
              <td>{row.value != null ? String(row.value) : '—'}</td>
              <td>{row.unit ?? '—'}</td>
              <td>{row.source}</td>
              <td>
                <span className={`inspector-badge inspector-badge--${row.status}`}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
