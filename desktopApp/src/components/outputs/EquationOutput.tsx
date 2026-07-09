import { DisplayMath, EngineeringMathText, InlineMath, isEngineeringSymbol } from '@/components/math/engineeringMath'
import { ReferenceChipList } from '@/components/outputs/ReferenceChipList'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'

import type {
  EquationInputTableRowDto,
  EquationOutputBlock,
  ReferenceChipDto,
  ReferenceLinkDto,
  ValueProvenanceDto,
} from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'
import '@/components/outputs/OutputRenderer.css'

interface EquationOutputProps {
  block: EquationOutputBlock
}

const AWAITING_USER_INPUT = 'Awaiting user input'

function renderInputTableCell(columnKey: string, value: string, pending = false) {
  const isPending = columnKey === 'value' && (pending || value === AWAITING_USER_INPUT)
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

function provenanceChips(row: EquationInputTableRowDto): ReferenceChipDto[] | undefined {
  const nested = row.value_provenance?.reference_chips
  if (nested?.length) {
    return nested
  }
  return row.reference_chips
}

function renderRowReferenceChips(chips?: ReferenceChipDto[]) {
  return <ReferenceChipList chips={chips} className="reference-chip-list--inline" />
}

function renderProvenanceTrail(provenance: ValueProvenanceDto, row: EquationInputTableRowDto) {
  const chips = provenanceChips(row)
  return (
    <span className="output-equation__value-provenance">
      <span className="output-equation__value-provenance-label">{provenance.label}</span>
      {chips?.length ? (
        <>
          {' '}
          {renderRowReferenceChips(chips)}
        </>
      ) : null}
      {provenance.detail ? (
        <span className="output-equation__value-provenance-detail"> {provenance.detail}</span>
      ) : null}
    </span>
  )
}

function chipKey(chip: ReferenceChipDto): string {
  return `${chip.ref_type}:${chip.id}`
}

function collectRowReferenceKeys(row: EquationInputTableRowDto): Set<string> {
  const keys = new Set<string>()
  const provenance = row.value_provenance
  if (provenance?.reference_chips?.length) {
    for (const chip of provenance.reference_chips) {
      keys.add(chipKey(chip))
    }
  }
  const reference = row.value_reference
  if (reference?.node_id) {
    keys.add(`node:${reference.node_id}`)
  }
  const defRef = row.definition_reference
  if (defRef?.node_id) {
    keys.add(`node:${defRef.node_id}`)
  }
  return keys
}

function renderValueCell(row: EquationInputTableRowDto) {
  const value = String(row.value ?? '')
  const provenance = row.value_provenance
  const reference = row.value_reference
  const chips = provenanceChips(row)

  if (provenance) {
    const hasResolvedValue = provenance.status === 'resolved' && Boolean(value && value !== AWAITING_USER_INPUT)

    if (provenance.status === 'awaiting_user_input') {
      return renderInputTableCell('value', AWAITING_USER_INPUT, true)
    }

    if (provenance.status === 'pending_derived') {
      return (
        <span className="output-equation__value-cell output-equation__value-cell--pending-derived">
          {renderProvenanceTrail(provenance, row)}
        </span>
      )
    }

    if (hasResolvedValue && provenance.source_type !== 'user_input') {
      return (
        <span className="output-equation__value-cell">
          {renderInputTableCell('value', value)}
          <span className="output-equation__value-provenance">
            {' '}
            derived from{' '}
            {chips?.length ? renderRowReferenceChips(chips) : reference ? renderReferenceLink(reference) : null}
          </span>
        </span>
      )
    }

    if (hasResolvedValue) {
      return renderInputTableCell('value', value)
    }
  }

  const hasResolvedValue = Boolean(value && value !== AWAITING_USER_INPUT)

  if (hasResolvedValue && reference) {
    return (
      <span className="output-equation__value-cell">
        {renderInputTableCell('value', value)}
        <span className="output-equation__value-provenance">
          {' '}
          derived from{' '}
          {chips?.length ? renderRowReferenceChips(chips) : renderReferenceLink(reference)}
        </span>
      </span>
    )
  }

  if (hasResolvedValue && chips?.length) {
    return (
      <span className="output-equation__value-cell">
        {renderInputTableCell('value', value)}
        <span className="output-equation__value-provenance">
          {' '}
          derived from {renderRowReferenceChips(chips)}
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
        derived from{' '}
        {chips?.length ? renderRowReferenceChips(chips) : renderReferenceLink(reference)}
      </span>
    )
  }

  return renderInputTableCell('value', value || AWAITING_USER_INPUT, true)
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

function mathExpressionsForBlock(block: EquationOutputBlock): string[] {
  const trace = block.equation_display_trace
  if (trace?.status === 'evaluated') {
    const expressions: string[] = []
    if (trace.symbolic_latex) {
      expressions.push(trace.symbolic_latex)
    }
    if (trace.substituted_latex) {
      expressions.push(trace.substituted_latex)
    } else if (trace.result_latex && trace.symbolic_latex) {
      expressions.push(`${trace.symbolic_latex} = ${trace.result_latex}`)
    }
    if (expressions.length > 0) {
      return expressions
    }
  }

  if (trace?.symbolic_latex && trace.status === 'blocked') {
    return [trace.symbolic_latex]
  }

  return block.content ? [block.content] : []
}

export function EquationOutput({ block }: EquationOutputProps) {
  const trace = block.equation_display_trace
  const mathExpressions = mathExpressionsForBlock(block)
  const rowReferenceKeys = new Set<string>()
  if (block.input_table?.rows) {
    for (const row of block.input_table.rows) {
      for (const key of collectRowReferenceKeys(row)) {
        rowReferenceKeys.add(key)
      }
    }
  }
  const footerChips = (block.reference_chips ?? []).filter(
    (chip) => !rowReferenceKeys.has(chipKey(chip)),
  )

  return (
    <article className="output-block output-equation">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      <div className="output-equation__math-row">
        {mathExpressions.map((expression, index) => (
          <DisplayMath
            key={`${block.id}-math-${index}`}
            expression={expression}
            className="output-equation__math"
          />
        ))}
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
                          : renderInputTableCell(
                              column.key,
                              String(row[column.key as keyof EquationInputTableRowDto] ?? ''),
                            )}
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
      {footerChips.length ? <ReferenceChipList chips={footerChips} /> : null}
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
      {block.result && trace?.status !== 'evaluated' ? (
        <p className="output-equation__result">
          {block.result.label}: {block.result.value}
          {block.result.unit ? ` ${block.result.unit}` : ''}
        </p>
      ) : null}
    </article>
  )
}
