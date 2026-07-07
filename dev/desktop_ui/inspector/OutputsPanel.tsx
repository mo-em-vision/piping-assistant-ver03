import type { TaskOutputRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type OutputsPanelProps = {
  rows: TaskOutputRowDto[]
}

export function OutputsPanel({ rows }: OutputsPanelProps) {
  if (!rows.length) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Outputs produced</h3>
        <p className="inspector-empty">No outputs produced yet.</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Outputs produced</h3>
      <table className="inspector-table">
        <thead>
          <tr>
            <th>Output</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Producing node</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field}>
              <td>
                <strong>{row.label}</strong>
                <div className="inspector-rationale-meta">{row.field}</div>
              </td>
              <td>{row.value != null ? String(row.value) : '—'}</td>
              <td>{row.unit ?? '—'}</td>
              <td>{row.producing_node ?? '—'}</td>
              <td>
                <span className={`inspector-badge inspector-badge--${row.status}`}>
                  {row.status}
                </span>
                {row.warnings.length ? (
                  <ul className="inspector-warning-list">
                    {row.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
