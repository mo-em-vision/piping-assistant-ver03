import type { ReactNode } from 'react'

import './InspectorPanels.css'

type InspectorDisclosureSectionProps = {
  title: string
  summary?: string
  defaultOpen?: boolean
  children: ReactNode
}

export function InspectorDisclosureSection({
  title,
  summary,
  defaultOpen = false,
  children,
}: InspectorDisclosureSectionProps) {
  return (
    <details className="inspector-disclosure" open={defaultOpen}>
      <summary className="inspector-disclosure__summary">
        <span className="inspector-disclosure__title">{title}</span>
        {summary ? <span className="inspector-disclosure__hint">{summary}</span> : null}
      </summary>
      <div className="inspector-disclosure__body">{children}</div>
    </details>
  )
}
