import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  EngineeringMathText,
  extractText,
  isEngineeringSymbol,
  isEquationLike,
  isInequalityLike,
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

describe('EngineeringMathText', () => {
  it('renders inline symbols and equations in plain text', () => {
    const { container } = render(
      <EngineeringMathText text="Minimum thickness T must meet t_m using t_m = t + c." />,
    )

    expect(container.querySelectorAll('.katex').length).toBeGreaterThanOrEqual(3)
  })
})
