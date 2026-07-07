import './InspectorPanels.css'

type PlannerWarningsPanelProps = {
  warnings: string[]
  planValid?: boolean | null
  planValidationMessages?: string[]
}

export function PlannerWarningsPanel({
  warnings,
  planValid,
  planValidationMessages = [],
}: PlannerWarningsPanelProps) {
  const staleSignals: string[] = []
  if (planValid === false) {
    staleSignals.push('Engineering plan failed client-side shape validation.')
  }
  if (planValid === true) {
    staleSignals.push('Valid normalized engineering plan.')
  }

  const allWarnings = [...staleSignals, ...planValidationMessages, ...warnings]
  if (!allWarnings.length) {
    return null
  }

  return (
    <section className="inspector-workflow-status__section">
      <h3 className="inspector-workflow-status__title">Warnings</h3>
      <ul className="inspector-warning-list">
        {allWarnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  )
}
