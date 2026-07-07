import type { TaskDecisionRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type DecisionsPanelProps = {
  rows: TaskDecisionRowDto[]
}

export function DecisionsPanel({ rows }: DecisionsPanelProps) {
  if (!rows.length) {
    return null
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Decisions and assumptions</h3>
      <table className="inspector-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Selected value</th>
            <th>Source</th>
            <th>Activated branch</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.kind}-${row.field}`}>
              <td>
                <strong>{row.field}</strong>
                <div className="inspector-rationale-meta">{row.kind}</div>
              </td>
              <td>{row.value != null ? String(row.value) : '—'}</td>
              <td>{row.source}</td>
              <td>{row.activated_branch ?? row.selected_node ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
