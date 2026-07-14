import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import type { EquationInputTableRowDto, EquationOutputBlock } from '@/types/backend/outputs'

function parameterNodeId(parameter: ParameterDefinitionDto): string | null {
  const nodeId = parameter.provenance?.node_id?.trim()
  return nodeId || null
}

function rowParameterId(row: EquationInputTableRowDto): string | null {
  const direct = row.parameter_id?.trim()
  if (direct) {
    return direct
  }
  const provenance = row.value_provenance?.source_ref?.parameter_id?.trim()
  return provenance || null
}

function rowMatchesParameter(
  row: EquationInputTableRowDto,
  parameter: ParameterDefinitionDto,
  block: EquationOutputBlock,
): boolean {
  const paramNodeId = parameterNodeId(parameter)
  if (!paramNodeId) {
    return false
  }

  const rowParamId = rowParameterId(row)
  if (rowParamId) {
    return rowParamId === paramNodeId
  }

  const rowSymbol = row.symbol?.trim()
  const traceInputs = block.equation_display_trace?.inputs ?? []
  return traceInputs.some(
    (input) =>
      input.parameter_id?.trim() === paramNodeId &&
      (!rowSymbol || rowSymbol === input.symbol?.trim()),
  )
}

export function findActiveEquationRowIndex(
  block: EquationOutputBlock,
  parameter: ParameterDefinitionDto | null,
): number | null {
  if (!parameter || !block.input_table?.rows?.length) {
    return null
  }

  const index = block.input_table.rows.findIndex((row) =>
    rowMatchesParameter(row, parameter, block),
  )
  return index === -1 ? null : index
}

export function isActivePreviewEquationBlock(block: EquationOutputBlock): boolean {
  if (block.type !== 'equation' || !block.input_table?.rows?.length) {
    return false
  }
  const state = block.display_state
  return state === 'preview' || state === 'active' || state == null
}
