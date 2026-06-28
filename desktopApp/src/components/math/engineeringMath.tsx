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

export function isLatexExpression(text: string): boolean {
  const normalized = text.trim()
  if (!normalized || normalized.includes('\n')) {
    return false
  }
  return /\\(?:frac|tag|mathrm|sqrt|text|left|right)\b/.test(normalized)
}

export function isMathExpression(text: string): boolean {
  return (
    isEquationLike(text) ||
    isInequalityLike(text) ||
    isDisplayEquationLike(text) ||
    isLatexExpression(text)
  )
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

function extractEquationTag(text: string): { body: string; tag: string } {
  const tagMatch = text.match(/\\tag\{[^}]+\}/)
  if (!tagMatch) {
    return { body: text, tag: '' }
  }
  return {
    body: text.replace(tagMatch[0], '').trim(),
    tag: tagMatch[0],
  }
}

function appendEquationTag(text: string, tag: string): string {
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (!tag) {
    return normalized
  }
  return `${normalized} ${tag}`
}

function convertSlashNotationToFrac(text: string): string {
  if (text.includes('\\frac')) {
    return text
  }

  let converted = text.replace(/\b([A-Z])([a-z])(?=[_/\\s<>=]|$)/g, '$1_$2')

  if (converted.includes(' = ') && converted.includes('/')) {
    const [left, right] = converted.split(' = ', 2)
    if (right) {
      const slashIndex = right.indexOf('/')
      if (slashIndex > 0) {
        const numerator = right.slice(0, slashIndex).trim()
        const denominator = right.slice(slashIndex + 1).trim()
        return `${left.trim()} = \\frac{${numerator}}{${denominator}}`
      }
    }
  }

  converted = converted.replace(
    /([A-Za-z][A-Za-z0-9_]*)\s*\/\s*([A-Za-z0-9_.()+\-]+)/g,
    '\\frac{$1}{$2}',
  )

  if (converted.includes(' = ') && converted.includes(' / ')) {
    const [left, right] = converted.split(' = ', 2)
    if (right?.includes(' / ') && !right.includes('\\frac')) {
      const [numerator, denominator] = right.split(' / ', 2)
      return `${left.trim()} = \\frac{${numerator.trim()}}{${denominator.trim()}}`
    }
  }

  return converted
}

export function toKatexExpression(expression: string): string {
  let text = expression
    .trim()
    .replace(/≤/g, '\\leq ')
    .replace(/≥/g, '\\geq ')
    .replace(/<=/g, '\\leq ')
    .replace(/>=/g, '\\geq ')

  const { body, tag } = extractEquationTag(text)
  text = body

  if (text.includes('\\frac') || isLatexExpression(text)) {
    return appendEquationTag(text, tag)
  }

  return appendEquationTag(convertSlashNotationToFrac(text), tag)
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

const INLINE_LATEX_PATTERN = /\$([^$\n]+?)\$/g

function renderPlainEngineeringText(text: string): ReactNode[] {
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

export function renderEngineeringText(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let lastIndex = 0

  for (const match of text.matchAll(INLINE_LATEX_PATTERN)) {
    const index = match.index ?? 0
    if (index > lastIndex) {
      nodes.push(...renderPlainEngineeringText(text.slice(lastIndex, index)))
    }

    const expression = match[1]?.trim() ?? ''
    if (expression) {
      nodes.push(<InlineMath key={`latex-${index}`} expression={expression} />)
    } else {
      nodes.push(match[0])
    }

    lastIndex = index + match[0].length
  }

  if (lastIndex < text.length) {
    nodes.push(...renderPlainEngineeringText(text.slice(lastIndex)))
  }

  return nodes.length > 0 ? nodes : renderPlainEngineeringText(text)
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
