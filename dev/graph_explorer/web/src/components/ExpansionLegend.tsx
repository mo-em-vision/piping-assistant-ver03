export default function ExpansionLegend() {
  const nodeStatuses = [
    ['awaiting_expansion_assumption', 'Awaiting assumption'],
    ['awaiting_decision', 'Awaiting decision'],
    ['awaiting_input', 'Awaiting input'],
    ['active', 'Active'],
    ['executed', 'Executed'],
    ['skipped', 'Skipped'],
    ['blocked', 'Blocked'],
  ]

  return (
    <div className="expansion-legend">
      <div className="section-title">Legend</div>
      <ul className="expansion-legend__list">
        {nodeStatuses.map(([status, label]) => (
          <li key={status}>
            <span className={`legend-swatch legend-swatch--${status}`} />
            {label}
          </li>
        ))}
      </ul>
      <div className="expansion-legend__edges">
        <div><span className="legend-edge legend-edge--solid" /> Active dependency</div>
        <div><span className="legend-edge legend-edge--dashed" /> Skipped / conditional</div>
        <div><span className="legend-edge legend-edge--dotted" /> Reference</div>
      </div>
    </div>
  )
}
