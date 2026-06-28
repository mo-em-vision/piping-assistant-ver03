import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  DisplayMath,
  EngineeringMathText,
  extractText,
  isEngineeringSymbol,
  isEquationLike,
  isInequalityLike,
  normalizeBareDisplayEquations,
  renderEngineeringText,
  toKatexExpression,
} from '@/components/math/engineeringMath'

describe('engineeringMath', () => {
  it('extracts text from nested React elements', () => {
    const nested = <code>t_m = t + c</code>
    expect(extractText(nested)).toBe('t_m = t + c')
    expect(isEquationLike(extractText(nested))).toBe(true)
  })

  it('recognizes engineering symbols used in nomenclature tables', () => {
    expect(isEngineeringSymbol('t_m')).toBe(true)
    expect(isEngineeringSymbol('P')).toBe(true)
    expect(isEngineeringSymbol('thickness')).toBe(false)
  })

  it('recognizes inequality expressions used in standards prose', () => {
    expect(isInequalityLike('Do/t < 10')).toBe(true)
    expect(isInequalityLike('t < D/6')).toBe(true)
  })

  it('routes latex equations with \\frac through a single inline math node', () => {
    const text = 't = \\frac{PD}{2(SEW + PY)}'
    const nodes = renderEngineeringText(text)
    expect(nodes).toHaveLength(1)
    expect(isEquationLike(text)).toBe(true)
  })

  it('converts slash equations with \\tag to stacked fractions', () => {
    const latex = toKatexExpression('t = PD/2(SEW + PY) \\tag{3a}')
    expect(latex).toContain('\\frac{PD}{2(SEW + PY)}')
    expect(latex).toContain('\\tag{3a}')
  })

  it('preserves existing \\frac when \\tag is present', () => {
    const input = 't = \\frac{PD}{2(SEW + PY)} \\tag{3a}'
    expect(toKatexExpression(input)).toBe(input)
  })

  it('converts inequality slash notation to \\frac', () => {
    expect(toKatexExpression('t < D/6')).toContain('\\frac{D}{6}')
  })
})

describe('normalizeBareDisplayEquations', () => {
  it('wraps bare display equations in fenced code blocks', () => {
    const input = `Paragraph text:

$$
 t = PD/2(SEW + PY)
\\tag{3a}
$$

Following text.`

    const result = normalizeBareDisplayEquations(input)

    expect(result).toContain('```\n$$\n t = PD/2(SEW + PY)\n\\tag{3a}\n$$\n```')
    expect(result).toContain('Following text.')
  })

  it('leaves already-fenced display equations unchanged', () => {
    const input = `Paragraph text:

\`\`\`
$$
t_m = t + c
\\tag{2}
$$
\`\`\`

Following text.`

    expect(normalizeBareDisplayEquations(input)).toBe(input)
  })

  it('handles multiple bare display equations in one body', () => {
    const input = `**(a)** For t < D/6:

$$
 t = PD/2(SEW + PY)
\\tag{3a}
$$

$$
t = P(d+2c)/2(SEW - P(1-Y))
\\tag{3b}
$$

**(b)** For t >= D/6.`

    const result = normalizeBareDisplayEquations(input)

    expect(result).toContain('\\tag{3a}')
    expect(result).toContain('\\tag{3b}')
    expect(result.match(/```/g)?.length).toBe(4)
  })
})

describe('EngineeringMathText', () => {
  it('renders inline symbols and equations in plain text', () => {
    const { container } = render(
      <EngineeringMathText text="Minimum thickness T must meet t_m using t_m = t + c." />,
    )

    expect(container.querySelectorAll('.katex').length).toBeGreaterThanOrEqual(3)
  })

  it('renders standard inline LaTeX delimiters with fractions', () => {
    const { container } = render(
      <EngineeringMathText text={'For $t < \\frac{D}{6}$, use equation (3a).'} />,
    )

    expect(container.querySelectorAll('.katex').length).toBeGreaterThanOrEqual(1)
    expect(container.querySelector('.katex .mfrac, .katex .frac-line')).toBeTruthy()
  })

  it('renders equations containing \\frac without dollar delimiters', () => {
    const text = 't = \\frac{PD}{2(SEW + PY)}'
    const { container } = render(<EngineeringMathText text={text} />)

    expect(container.querySelector('.katex .mfrac, .katex .frac-line')).toBeTruthy()
  })

  it('renders legacy slash equations with equation tags as stacked fractions', () => {
    const { container } = render(
      <DisplayMath expression={'t = PD/2(SEW + PY) \\tag{3a}'} className="standards-markdown__equation" />,
    )

    expect(container.querySelector('.katex .mfrac, .katex .frac-line')).toBeTruthy()
    expect(container.querySelector('.katex .tag')).toBeTruthy()
  })
})
