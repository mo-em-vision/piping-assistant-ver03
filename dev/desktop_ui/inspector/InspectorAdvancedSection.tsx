import './InspectorPanels.css'

type InspectorAdvancedSectionProps = {
  title: string
  data: unknown
  deprecated?: boolean
}

export function InspectorAdvancedSection({ title, data, deprecated }: InspectorAdvancedSectionProps) {
  return (
    <details className="inspector-advanced">
      <summary>
        {title}
        {deprecated ? <span className="inspector-advanced__deprecated"> (deprecated — not canonical)</span> : null}
      </summary>
      <p className="inspector-advanced__note">
        Raw JSON fallback for fields not yet covered by readable inspector projections.
      </p>
      <pre className="inspector-code inspector-code--tall">{JSON.stringify(data, null, 2)}</pre>
    </details>
  )
}
