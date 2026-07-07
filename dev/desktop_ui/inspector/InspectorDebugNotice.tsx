import './InspectorPanels.css'

export function InspectorDebugNotice() {
  return (
    <p className="inspector-debug-notice" role="note">
      Developer / debug view only. Status, reasons, and labels come from backend inspection
      projections — not Flow Guidance and not product UI copy.
    </p>
  )
}

type InspectorDebugFieldProps = {
  label: string
  value: string
}

export function InspectorDebugField({ label, value }: InspectorDebugFieldProps) {
  return (
    <div>
      <dt>
        {label}
        <span className="inspector-debug-field__tag">Inspector debug</span>
      </dt>
      <dd>{value}</dd>
    </div>
  )
}
