import { Fragment, isValidElement, type ReactNode, useEffect, useRef } from 'react'
import katex from 'katex'

import 'katex/dist/katex.min.css'

const LOWERCASE_SYMBOLS = new Set(['c', 'd', 't'])

export function extractText(children: ReactNode): string {
  if (children == null || children === false) {
    return ''
  }
  if (typeof children === 'string' || typeof children === 'number') {
    return String(children)
  }
  if (Array.isArray(children)) {
    return children.map((child) => extractText(child)).join('')
  }
  if (typeof children === 'object' && 'props' in children && children.props != null) {
    return extractText((children.props as { children?: ReactNode }).children)
  }
  return ''
}

export function isEquationLike(text: string): boolean {
  const normalized = text.trim()
  if (!normalized || !normalized.includes('=')) {
    return false
  }
  if (normalized.includes('\n')) {
    return false
  }
  return normalized.length <= 120
}

export function normalizeDisplayEquation(text: string): string | null {
  const lines = text
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && line !== '$$')

  if (lines.length === 0) {
    return null
  }

  const normalized = lines.join(' ')
  if (!normalized.includes('=')) {
    return null
  }
  if (normalized.length > 200) {
    return null
  }
  return normalized
}

export function isDisplayEquationLike(text: string): boolean {
  return normalizeDisplayEquation(text) != null
}

const FENCED_BLOCK_PATTERN = /```[\s\S]*?```/g
const BARE_DISPLAY_EQUATION_PATTERN = /(^|\n)\$\$\s*\n([\s\S]*?)\n\$\$\s*(?=\n|$)/g

function wrapBareDisplayEquationsInSegment(segment: string): string {
  return segment.replace(BARE_DISPLAY_EQUATION_PATTERN, (match, before, equationBody) => {
    return `${before}\`\`\`\n$$\n${equationBody}\n$$\n\`\`\``
  })
}

export function normalizeBareDisplayEquations(markdown: string): string {
  const parts = markdown.split(FENCED_BLOCK_PATTERN)
  const fences = markdown.match(FENCED_BLOCK_PATTERN) ?? []

  if (fences.length === 0) {
    return wrapBareDisplayEquationsInSegment(markdown)
  }

  let result = wrapBareDisplayEquationsInSegment(parts[0] ?? '')
  for (let index = 0; index < fences.length; index += 1) {
    result += fences[index]
    result += wrapBareDisplayEquationsInSegment(parts[index + 1] ?? '')
  }
  return result
}

export function isInequalityLike(text: string): boolean {
  const normalized = text.trim()
  if (!normalized || normalized.includes('\n') || normalized.length > 120) {
    return false
  }
  return /^(?:[A-Za-z][A-Za-z0-9_]*(?:\s*\/\s*[A-Za-z][A-Za-z0-9_]*)?\s*(?:<|>|≤|≥|<=|>=)\s*[A-Za-z0-9_.]+(?:\s*\/\s*[A-Za-z0-9_.]+)?)$/.test(
    normalized,
  )
}

export function isMathExpression(text: string): boolean {
  return isEquationLike(text) || isInequalityLike(text) || isDisplayEquationLike(text)
}

export function isInlineSymbol(text: string): boolean {
  const normalized = text.trim()
  if (!normalized || normalized.includes('\n') || normalized.includes(' ')) {
    return false
  }
  if (normalized.length > 12) {
    return false
  }
  if (/[-./]/.test(normalized)) {
    return false
  }
  return /^[A-Za-z][A-Za-z0-9_]*$/.test(normalized)
}

export function isEngineeringSymbol(text: string): boolean {
  const normalized = text.trim()
  if (!isInlineSymbol(normalized)) {
    return false
  }
  if (normalized.includes('_')) {
    return true
  }
  if (/^[A-Z]$/.test(normalized)) {
    return true
  }
  return LOWERCASE_SYMBOLS.has(normalized)
}

export function toKatexExpression(expression: string): string {
  let text = expression.trim()
  if (text.includes('\\tag') || text.includes('\\frac')) {
    return text.replace(/\s+/g, ' ').trim()
  }

  text = text
    .replace(/≤/g, '\\leq ')
    .replace(/≥/g, '\\geq ')
    .replace(/<=/g, '\\leq ')
    .replace(/>=/g, '\\geq ')
    .replace(/\b([A-Z])([a-z])(?=[_/\\s<>=]|$)/g, '$1_$2')

  text = text.replace(
    /([A-Za-z][A-Za-z0-9_]*)\s*\/\s*([A-Za-z][A-Za-z0-9_]*)/g,
    '\\frac{$1}{$2}',
  )

  if (text.includes(' = ') && text.includes(' / ')) {
    const [left, right] = text.split(' = ', 2)
    if (right?.includes(' / ') && !right.includes('\\frac')) {
      const [numerator, denominator] = right.split(' / ', 2)
      return `${left.trim()} = \\frac{${numerator.trim()}}{${denominator.trim()}}`
    }
  }

  return text.replace(/\s+/g, ' ').trim()
}

export function InlineMath({
  expression,
  className,
}: {
  expression: string
  className?: string
}) {
  const mathRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!mathRef.current) {
      return
    }
    katex.render(toKatexExpression(expression), mathRef.current, {
      throwOnError: false,
      displayMode: false,
    })
  }, [expression])

  return (
    <span
      ref={mathRef}
      className={className ? `engineering-math-inline ${className}` : 'engineering-math-inline'}
    />
  )
}

export function DisplayMath({
  expression,
  className,
}: {
  expression: string
  className?: string
}) {
  const mathRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mathRef.current) {
      return
    }
    katex.render(toKatexExpression(expression), mathRef.current, {
      throwOnError: false,
      displayMode: true,
    })
  }, [expression])

  return (
    <div
      ref={mathRef}
      className={className ? `engineering-math-display ${className}` : 'engineering-math-display'}
    />
  )
}

const ENGINEERING_TEXT_PATTERN =
  /([A-Za-z][A-Za-z0-9_]*(?:\s*\/\s*[A-Za-z][A-Za-z0-9_]*)?\s*(?:<|>|≤|≥|<=|>=)\s*[A-Za-z0-9_.]+(?:\s*\/\s*[A-Za-z0-9_.]+)?)|([A-Za-z][A-Za-z0-9_]*\s*=\s*[^.,;\n]+)|([A-Za-z][A-Za-z0-9_]*)/g

export function renderEngineeringText(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let lastIndex = 0

  for (const match of text.matchAll(ENGINEERING_TEXT_PATTERN)) {
    const index = match.index ?? 0
    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index))
    }

    const inequality = match[1]?.trim()
    const equation = match[2]?.trim()
    const symbol = match[3]?.trim()

    if (inequality && isInequalityLike(inequality)) {
      nodes.push(<InlineMath key={`ineq-${index}`} expression={inequality} />)
    } else if (equation && isEquationLike(equation)) {
      nodes.push(<InlineMath key={`eq-${index}`} expression={equation} />)
    } else if (symbol && isEngineeringSymbol(symbol)) {
      nodes.push(<InlineMath key={`sym-${index}`} expression={symbol} />)
    } else {
      nodes.push(match[0])
    }

    lastIndex = index + match[0].length
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex))
  }

  return nodes.length > 0 ? nodes : [text]
}

export function renderRichEngineeringContent(children: ReactNode): ReactNode {
  if (children == null || children === false) {
    return null
  }
  if (typeof children === 'string') {
    return renderEngineeringText(children)
  }
  if (Array.isArray(children)) {
    return children.map((child, index) => (
      <Fragment key={index}>{renderRichEngineeringContent(child)}</Fragment>
    ))
  }
  if (isValidElement(children)) {
    return children
  }
  return children
}

export function EngineeringMathText({
  text,
  className,
}: {
  text: string
  className?: string
}) {
  return <span className={className}>{renderEngineeringText(text)}</span>
}
