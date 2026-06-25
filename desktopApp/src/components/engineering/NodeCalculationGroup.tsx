import { useState } from 'react'

import type { NodeCalculationSummaryDto } from '@/types/backend/api'

import './NodeCalculationGroup.css'

type NodeCalculationGroupProps = {
  summary: NodeCalculationSummaryDto
}

function nodeLabel(summary: NodeCalculationSummaryDto): string {
  if (summary.paragraph) {
    return `\u00a7${summary.paragraph}`
  }
  return summary.title
}

export function NodeCalculationGroup({ summary }: NodeCalculationGroupProps) {
  const [expanded, setExpanded] = useState(false)
  const { primary_result: result } = summary
  const resultText = result.unit ? `${result.value} ${result.unit}` : result.value

  return (
    <div className="node-calc-group">
      <button
        type="button"
        className="node-calc-group__header"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span className="node-calc-group__label">{nodeLabel(summary)}</span>
        <span className="node-calc-group__result">
          {result.symbol} = {resultText}
        </span>
        <span className="node-calc-group__toggle" aria-hidden="true">
          {expanded ? '\u2212' : '+'}
        </span>
      </button>
      {expanded && summary.inputs.length ? (
        <ul className="node-calc-group__inputs">
          {summary.inputs.map((input) => (
            <li key={input.symbol} className="node-calc-group__input-row">
              <span className="node-calc-group__symbol">{input.symbol}</span>
              <span className="node-calc-group__input-name">{input.name}</span>
              <span className="node-calc-group__input-value">
                {input.value}
                {input.unit ? ` ${input.unit}` : ''}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
