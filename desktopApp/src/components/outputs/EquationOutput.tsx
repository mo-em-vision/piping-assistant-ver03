import { DisplayMath, EngineeringMathText, InlineMath, isEngineeringSymbol } from '@/components/math/engineeringMath'
import { ReferenceChipList } from '@/components/outputs/ReferenceChipList'
import { StandardReferenceLink } from '@/components/standards/StandardReferenceLink'
import { equationPresentationLines } from '@/utils/equationPresentationLines'

import type {
  EquationInputTableRowDto,
  EquationOutputBlock,
  ReferenceChipDto,
  ReferenceLinkDto,
  TableColumnDto,
  ValueProvenanceDto,
} from '@/types/backend/outputs'

import '@/components/math/engineeringMath.css'
import '@/components/outputs/OutputRenderer.css'

interface EquationOutputProps {
  block: EquationOutputBlock
}

const AWAITING_USER_INPUT = 'Awaiting user input'
const EMPTY_CELL = '—'

function rowDescription(row: EquationInputTableRowDto): string {
  return String(row.description ?? row.definition ?? '').trim()
}

function hasSourceColumn(columns: TableColumnDto[]): boolean {
  return columns.some((column) => column.key === 'source')
}

function renderInputTableCell(columnKey: string, value: string, pending = false) {
  const isPending = columnKey === 'value' && (pending || value === AWAITING_USER_INPUT)
  if (columnKey === 'symbol') {
    if (!value) {
      return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
    }
    if (isEngineeringSymbol(value)) {
      return <InlineMath expression={value} />
    }
  }
  if (!value) {
    return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
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

function primaryChip(chips?: ReferenceChipDto[]): ReferenceChipDto | undefined {
  return chips?.[0]
}

function renderProvenanceTrail(provenance: ValueProvenanceDto, row: EquationInputTableRowDto) {
  const chips = provenanceChips(row)
  const chip = primaryChip(chips)
  return (
    <span className="output-equation__value-provenance">
      <span className="output-equation__value-provenance-label">{provenance.label}</span>
      {chip ? (
        <>
          {' '}
          {renderRowReferenceChips([chip])}
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

function renderValueReference(row: EquationInputTableRowDto) {
  const chips = provenanceChips(row)
  const chip = primaryChip(chips)
  if (chip) {
    return renderRowReferenceChips([chip])
  }
  const reference = row.value_reference
  if (reference) {
    return renderReferenceLink(reference)
  }
  return null
}

function renderValueCell(row: EquationInputTableRowDto, sourceColumnPresent: boolean) {
  const value = String(row.value ?? '')
  const provenance = row.value_provenance

  if (provenance) {
    if (provenance.status === 'awaiting_user_input') {
      return renderInputTableCell('value', AWAITING_USER_INPUT, true)
    }

    if (provenance.status === 'pending_derived') {
      if (sourceColumnPresent) {
        return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
      }
      return (
        <span className="output-equation__value-cell output-equation__value-cell--pending-derived">
          {renderProvenanceTrail(provenance, row)}
        </span>
      )
    }

    if (value && value !== AWAITING_USER_INPUT) {
      return renderInputTableCell('value', value)
    }
  }

  const hasResolvedValue = Boolean(value && value !== AWAITING_USER_INPUT)
  if (hasResolvedValue) {
    return renderInputTableCell('value', value)
  }

  if (!sourceColumnPresent && (row.value_reference || provenanceChips(row)?.length)) {
    return (
      <span className="output-equation__value-cell">
        {renderValueReference(row)}
      </span>
    )
  }

  return renderInputTableCell('value', value || AWAITING_USER_INPUT, true)
}

function renderDescriptionCell(row: EquationInputTableRowDto) {
  const description = rowDescription(row)
  const reference = row.definition_reference
  if (!description && !reference) {
    return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
  }
  if (!reference) {
    return <EngineeringMathText text={description} />
  }

  return (
    <span className="output-equation__definition-cell">
      {description ? <EngineeringMathText text={description} /> : null}
      {description ? ' — ' : null}
      {renderReferenceLink(reference)}
    </span>
  )
}

function renderParameterCell(row: EquationInputTableRowDto) {
  const parameter = String(row.parameter ?? '').trim()
  if (!parameter) {
    return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
  }
  return <EngineeringMathText text={parameter} />
}

function renderUnitCell(row: EquationInputTableRowDto) {
  const unit = String(row.unit ?? '').trim()
  if (!unit) {
    return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
  }
  return <EngineeringMathText text={unit} />
}

function renderSourceCell(row: EquationInputTableRowDto) {
  const provenance = row.value_provenance
  const sourceText = String(row.source ?? '').trim()
  const chips = provenanceChips(row)

  if (!sourceText && !chips?.length && !provenance) {
    return <span className="output-equation__input-empty">{EMPTY_CELL}</span>
  }

  return (
    <span className="output-equation__source-cell">
      {sourceText ? <EngineeringMathText text={sourceText} /> : null}
      {chips?.length ? (
        <span className="output-equation__source-chips">
          {sourceText ? ' ' : null}
          {renderRowReferenceChips(chips)}
        </span>
      ) : null}
      {!sourceText && !chips?.length && provenance ? (
        <span className="output-equation__value-provenance-label">{provenance.label}</span>
      ) : null}
    </span>
  )
}

function renderInputTableRowCell(
  column: TableColumnDto,
  row: EquationInputTableRowDto,
  sourceColumnPresent: boolean,
) {
  switch (column.key) {
    case 'definition':
    case 'description':
      return renderDescriptionCell(row)
    case 'parameter':
      return renderParameterCell(row)
    case 'value':
      return renderValueCell(row, sourceColumnPresent)
    case 'unit':
      return renderUnitCell(row)
    case 'source':
      return renderSourceCell(row)
    default:
      return renderInputTableCell(
        column.key,
        String(row[column.key as keyof EquationInputTableRowDto] ?? ''),
      )
  }
}

function renderInputTable(block: EquationOutputBlock) {
  if (!block.input_table) {
    return null
  }

  const sourceColumnPresent = hasSourceColumn(block.input_table.columns)

  return (
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
                  {renderInputTableRowCell(column, row, sourceColumnPresent)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function renderMathLine(blockId: string, suffix: string, expression: string) {
  return (
    <DisplayMath
      key={`${blockId}-${suffix}`}
      expression={expression}
      className={`output-equation__math output-equation__math--${suffix}`}
    />
  )
}

export function EquationOutput({ block }: EquationOutputProps) {
  const trace = block.equation_display_trace
  const presentation = equationPresentationLines(block)
  const isEvaluated = trace?.status === 'evaluated'
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

  const inputTable = renderInputTable(block)

  return (
    <article className="output-block output-equation">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      {block.context_intro ? (
        <p className="output-equation__context-intro">{block.context_intro}</p>
      ) : null}
      {block.context_lead ? (
        <p className="output-equation__context-lead">{block.context_lead}</p>
      ) : null}
      {presentation.symbolic
        ? renderMathLine(block.id, 'symbolic', presentation.symbolic)
        : null}
      {!isEvaluated ? inputTable : null}
      {!isEvaluated && !block.input_table && block.variables && block.variables.length > 0 ? (
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
      {presentation.substituted
        ? renderMathLine(block.id, 'substituted', presentation.substituted)
        : null}
      {presentation.result ? renderMathLine(block.id, 'result', presentation.result) : null}
      {isEvaluated ? inputTable : null}
      {!block.input_table && footerChips.length ? (
        <ReferenceChipList chips={footerChips} />
      ) : null}
      {!block.input_table && block.nomenclature_reference ? (
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
