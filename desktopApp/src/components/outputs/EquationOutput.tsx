import { DisplayMath, EngineeringMathText, InlineMath, isEngineeringSymbol } from '@/components/math/engineeringMath'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'

import type {
  EquationInputTableRowDto,
  EquationOutputBlock,
  ReferenceLinkDto,
} from '@/types/backend/outputs'

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

function renderReferenceLink(reference: ReferenceLinkDto) {
  const referenceKind = reference.reference_kind === 'table' ? 'table' : 'node'
  return (
    <StandardReferenceLink
      referenceKind={referenceKind}
      referenceId={reference.node_id}
      nodeId={reference.node_id}
      label={reference.label}
    />
  )
}

function renderValueCell(row: EquationInputTableRowDto) {
  const value = String(row.value ?? '')
  const reference = row.value_reference
  const hasResolvedValue = Boolean(value && value !== AWAITING_USER_INPUT)

  if (hasResolvedValue && reference) {
    return (
      <span className="output-equation__value-cell">
        {renderInputTableCell('value', value)}
        <span className="output-equation__value-provenance">
          {' '}
          derived from {renderReferenceLink(reference)}
        </span>
      </span>
    )
  }

  if (hasResolvedValue) {
    return renderInputTableCell('value', value)
  }

  if (reference) {
    return (
      <span className="output-equation__value-cell">
        derived from {renderReferenceLink(reference)}
      </span>
    )
  }
  return renderInputTableCell('value', value || AWAITING_USER_INPUT)
}

function renderDefinitionCell(row: EquationInputTableRowDto) {
  const definition = String(row.definition ?? '')
  const reference = row.definition_reference
  if (!reference) {
    return <EngineeringMathText text={definition} />
  }

  return (
    <span className="output-equation__definition-cell">
      <EngineeringMathText text={definition} /> (as defined in {renderReferenceLink(reference)})
    </span>
  )
}

export function EquationOutput({ block }: EquationOutputProps) {
  return (
    <article className="output-block output-equation">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <div className="output-equation__math-row">
        <DisplayMath expression={block.content} className="output-equation__math" />
      </div>
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
                      {column.key === 'definition'
                        ? renderDefinitionCell(row)
                        : column.key === 'value'
                          ? renderValueCell(row)
                          : renderInputTableCell(column.key, String(row[column.key as keyof EquationInputTableRowDto] ?? ''))}
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
      {block.nomenclature_reference &&
      !block.input_table?.rows.some((row) => row.definition_reference) ? (
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
