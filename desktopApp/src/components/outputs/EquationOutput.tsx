import { useEffect, useRef } from 'react'
import katex from 'katex'

import type { EquationOutputBlock } from '@/types/backend/outputs'

import 'katex/dist/katex.min.css'

interface EquationOutputProps {
  block: EquationOutputBlock
}

export function EquationOutput({ block }: EquationOutputProps) {
  const mathRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mathRef.current) {
      return
    }
    katex.render(block.content, mathRef.current, {
      throwOnError: false,
      displayMode: true,
    })
  }, [block.content])

  return (
    <article className="output-block output-equation">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <div ref={mathRef} className="output-equation__math" />
      {block.display ? <p className="output-equation__display">{block.display}</p> : null}
      {block.variables && block.variables.length > 0 ? (
        <dl className="output-equation__variables">
          {block.variables.map((variable) => (
            <div key={variable.symbol}>
              <dt>{variable.symbol}</dt>
              <dd>{variable.name}</dd>
              <dd>
                {variable.value != null
                  ? `${variable.value}${variable.unit ? ` ${variable.unit}` : ''}`
                  : ''}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {block.result ? (
        <p className="output-equation__result">
          {block.result.label}: {block.result.value}
          {block.result.unit ? ` ${block.result.unit}` : ''}
        </p>
      ) : null}
    </article>
  )
}
