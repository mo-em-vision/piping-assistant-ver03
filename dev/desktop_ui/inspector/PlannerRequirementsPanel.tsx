import type { PlannerRequirementRowDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type PlannerRequirementsPanelProps = {
  rows: PlannerRequirementRowDto[]
}

const CATEGORY_LABELS: Record<string, string> = {
  conditional: 'Conditional requirements',
  lookup_derived: 'Lookup-derived values',
  calculation: 'Calculation requirements',
  system_resolved: 'System-resolved requirements',
}

export function PlannerRequirementsPanel({ rows }: PlannerRequirementsPanelProps) {
  if (!rows.length) {
    return null
  }

  const grouped = rows.reduce<Record<string, PlannerRequirementRowDto[]>>((acc, row) => {
    const key = row.category
    if (!acc[key]) {
      acc[key] = []
    }
    acc[key].push(row)
    return acc
  }, {})

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Requirements</h3>
      {Object.entries(grouped).map(([category, categoryRows]) => (
        <div key={category} className="inspector-requirements-group">
          <h4 className="inspector-requirements-group__title">
            {CATEGORY_LABELS[category] ?? category.replaceAll('_', ' ')}
          </h4>
          <table className="inspector-table">
            <thead>
              <tr>
                <th>Requirement</th>
                <th>Status</th>
                <th>Depends on</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {categoryRows.map((row) => (
                <tr key={`${category}-${row.field}`}>
                  <td>
                    <strong>{row.label}</strong>
                    <div className="inspector-rationale-meta">{row.field}</div>
                    {row.resolution_label ? (
                      <span className="inspector-rationale-meta"> {row.resolution_label}</span>
                    ) : null}
                  </td>
                  <td>
                    <span className={`inspector-badge inspector-badge--${row.display_status}`}>
                      {row.display_status.replaceAll('_', ' ')}
                    </span>
                  </td>
                  <td>{row.depends_on.length ? row.depends_on.join(', ') : '—'}</td>
                  <td>{row.source_node_id ?? row.resolution_kind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  )
}
