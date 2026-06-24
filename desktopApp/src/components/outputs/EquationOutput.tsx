import { DisplayMath, EngineeringMathText, InlineMath, isEngineeringSymbol } from '@/components/math/engineeringMath'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'

import type { EquationOutputBlock } from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'
import '@/components/outputs/OutputRenderer.css'

interface EquationOutputProps {
  block: EquationOutputBlock
}

const AWAITING_USER_INPUT = 'Awaiting user input'

function renderInputTableCell(columnKey: string, value: string) {
  const isPending = columnKey === 'value' && value === AWAITING_USER_INPUT
  if (columnKey === 'symbol') {
    if (!value) {
      return <span className="output-equation__input-empty">—</span>
    }
    if (isEngineeringSymbol(value)) {
      return <InlineMath expression={value} />
    }
  }
  return (
    <span className={isPending ? 'output-equation__input-pending' : undefined}>
      <EngineeringMathText text={value} />
    </span>
  )
}

export function EquationOutput({ block }: EquationOutputProps) {
  return (
    <article className="output-block output-equation">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <DisplayMath expression={block.content} className="output-equation__math" />
      {block.input_table ? (
        <div className="output-equation__input-table">
          <table className="output-table">
            <thead>
              <tr>
                {block.input_table.columns.map((column) => (
                  <th key={column.key}>{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.input_table.rows.map((row, index) => (
                <tr key={`${block.id}-input-row-${index}`}>
                  {block.input_table!.columns.map((column) => (
                    <td key={column.key}>
                      {renderInputTableCell(column.key, String(row[column.key] ?? ''))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : block.variables && block.variables.length > 0 ? (
        <dl className="output-equation__variables">
          {block.variables.map((variable) => (
            <div key={variable.symbol}>
              <dt>
                <InlineMath expression={variable.symbol} />
              </dt>
              <dd>
                <EngineeringMathText text={variable.name} />
              </dd>
              <dd>
                {variable.value != null
                  ? `${variable.value}${variable.unit ? ` ${variable.unit}` : ''}`
                  : ''}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {block.nomenclature_reference ? (
        <p className="output-equation__nomenclature-ref">
          Symbols defined in{' '}
          <StandardReferenceLink
            nodeId={block.nomenclature_reference.node_id}
            label={block.nomenclature_reference.label}
          />
        </p>
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
