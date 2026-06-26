import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  EngineeringMathText,
  extractText,
  isEngineeringSymbol,
  isEquationLike,
  isInequalityLike,
  normalizeBareDisplayEquations,
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
})
