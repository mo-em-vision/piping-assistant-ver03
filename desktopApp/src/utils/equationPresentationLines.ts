import type { EquationDisplayTraceDto, EquationOutputBlock } from '@/types/backend/outputs'

export type EquationPresentationLines = {
  symbolic: string | null
  substituted: string | null
  result: string | null
}

function splitSubstitutedFromResult(
  substituted: string,
  resultLatex: string | null | undefined,
): string {
  if (!resultLatex?.trim()) {
    return substituted
  }

  const trimmedResult = resultLatex.trim()
  const suffix = ` = ${trimmedResult}`
  if (substituted.endsWith(suffix)) {
    return substituted.slice(0, -suffix.length)
  }

  if (substituted.includes(trimmedResult)) {
    const parts = substituted.split(' = ')
    if (parts.length > 1) {
      return parts.slice(0, -1).join(' = ')
    }
  }

  return substituted
}

function resultLineFromTrace(trace: EquationDisplayTraceDto): string | null {
  const resultLatex = trace.result_latex?.trim()
  if (!resultLatex) {
    return null
  }

  const symbol = trace.result?.symbol?.trim()
  if (symbol) {
    return `${symbol} = ${resultLatex}`
  }

  const symbolic = trace.symbolic_latex?.trim()
  if (symbolic?.includes('=')) {
    const lhs = symbolic.split('=')[0]?.trim()
    if (lhs) {
      return `${lhs} = ${resultLatex}`
    }
  }

  return resultLatex
}

export function equationPresentationLines(block: EquationOutputBlock): EquationPresentationLines {
  const trace = block.equation_display_trace

  if (!trace) {
    const fallback = block.content?.trim() || block.display?.trim() || null
    return { symbolic: fallback, substituted: null, result: null }
  }

  const symbolic = trace.symbolic_latex?.trim() || block.content?.trim() || null
  let substituted: string | null = null
  let result: string | null = null

  if (trace.substituted_latex?.trim()) {
    substituted = splitSubstitutedFromResult(trace.substituted_latex.trim(), trace.result_latex)
  }

  if (trace.status === 'evaluated') {
    result = resultLineFromTrace(trace)
  }

  return { symbolic, substituted, result }
}
