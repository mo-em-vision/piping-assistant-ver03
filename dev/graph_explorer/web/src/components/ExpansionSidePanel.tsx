import { useState } from 'react'

import type { ExpansionNode } from '../types'

interface ExpansionSidePanelProps {
  node: ExpansionNode | null
}

export default function ExpansionSidePanel({ node }: ExpansionSidePanelProps) {
  const [showRaw, setShowRaw] = useState(false)
  if (!node) {
    return (
      <aside className="panel expansion-side-panel">
        <p className="expansion-side-panel__empty">Select a node to inspect expansion state.</p>
      </aside>
    )
  }

  const execution = node.details.execution as Record<string, unknown> | undefined

  return (
    <aside className="panel expansion-side-panel">
      <h2>{node.label}</h2>
      <div className="expansion-side-panel__meta">
        <div><strong>ID</strong> {node.id}</div>
        <div><strong>Type</strong> {node.type}</div>
        <div><strong>Status</strong> {node.status}</div>
        <div><strong>Phase</strong> {node.phase}</div>
        <div><strong>Source</strong> {String(node.details.source ?? 'unknown')}</div>
      </div>
      <p className="expansion-side-panel__reason">{node.reason}</p>

      {node.missing_inputs.length > 0 && (
        <section>
          <div className="section-title">Missing inputs</div>
          <ul>{node.missing_inputs.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}

      {node.provided_outputs.length > 0 && (
        <section>
          <div className="section-title">Provided outputs</div>
          <ul>{node.provided_outputs.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}

      {execution && (
        <section>
          <div className="section-title">Execution</div>
          <pre className="expansion-side-panel__json">{JSON.stringify(execution, null, 2)}</pre>
        </section>
      )}

      <button type="button" className="toolbar-btn" onClick={() => setShowRaw((value) => !value)}>
        {showRaw ? 'Hide raw JSON' : 'Show raw JSON'}
      </button>
      {showRaw && <pre className="expansion-side-panel__json">{JSON.stringify(node, null, 2)}</pre>}
    </aside>
  )
}
