import type { PlannerDebugProjectionDto } from '@/types/backend/inspection'

import { displayValue } from './plannerDebugDisplay'

import './InspectorPanels.css'

type PlannerRequiredInputsSectionProps = {
  projection: PlannerDebugProjectionDto
}

export function PlannerRequiredInputsSection({ projection }: PlannerRequiredInputsSectionProps) {
  const rows = projection.required_inputs ?? []

  if (!rows.length) {
    return (
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Required Inputs</h3>
        <p className="inspector-empty">not available</p>
      </section>
    )
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Required Inputs</h3>
      <table className="inspector-table">
        <thead>
          <tr>
            <th>Symbol / key</th>
            <th>Name</th>
            <th>Status</th>
            <th>Input type</th>
            <th>Unit</th>
            <th>Reason required</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>
                <strong>{displayValue(row.symbol ?? row.key)}</strong>
                {row.symbol ? (
                  <div className="inspector-rationale-meta">{row.key}</div>
                ) : null}
              </td>
              <td>{displayValue(row.label)}</td>
              <td>
                <span className={`inspector-badge inspector-badge--${row.status}`}>
                  {row.status.replaceAll('_', ' ')}
                </span>
              </td>
              <td>{displayValue(row.expected_input_type)}</td>
              <td>{displayValue(row.unit)}</td>
              <td>{displayValue(row.reason_required)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
