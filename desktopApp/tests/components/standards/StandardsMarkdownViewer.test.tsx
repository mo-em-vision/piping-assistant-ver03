import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { StandardsMarkdownViewer } from '@/components/standards/StandardsMarkdownViewer'
import { useRightPanelStore } from '@/store/rightPanelStore'
const SAMPLE_BODY = `# Standard Paragraph Content

## (a)

The required thickness of straight sections of pipe shall be determined in accordance with eq. (2):

\`\`\`
t_m = t + c
\`\`\`

The minimum thickness, **T**, for the pipe selected shall be not less than **t_m**.

Design pressure is \`P\`.

## (b)

The following nomenclature is used in the equations for pressure design of straight pipe:

| Symbol | Description |
| ------ | ----------- |
| **c** | corrosion allowance |
| **t_m** | minimum required thickness |
`

describe('StandardsMarkdownViewer', () => {
  beforeEach(() => {
    useRightPanelStore.getState().reset()
  })

  it('renders headings and table content from standards markdown', () => {
    render(<StandardsMarkdownViewer content={SAMPLE_BODY} />)

    expect(screen.getByRole('heading', { name: 'Standard Paragraph Content' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '(a)' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Symbol' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Description' })).toBeInTheDocument()
    expect(screen.getByText('corrosion allowance')).toBeInTheDocument()
  })

  it('renders fenced equations with KaTeX instead of raw code fences', () => {
    const { container } = render(<StandardsMarkdownViewer content={SAMPLE_BODY} />)

    expect(container.querySelectorAll('.katex').length).toBeGreaterThanOrEqual(2)
    expect(screen.queryByText('```')).not.toBeInTheDocument()
  })

  it('renders fenced display equations with equation tags', () => {
    const content = `Paragraph text referencing eq. (2):

\`\`\`
$$
t_m = t + c
\\tag{2}
$$
\`\`\`

Following text.`

    const { container } = render(<StandardsMarkdownViewer content={content} />)

    expect(container.querySelector('.standards-markdown__equation .katex')).toBeTruthy()
    expect(container.querySelector('.katex .tag')).toBeTruthy()
  })

  it('renders table symbols and inline code symbols with KaTeX', () => {
    const { container } = render(<StandardsMarkdownViewer content={SAMPLE_BODY} />)

    const symbolCells = container.querySelectorAll('.standards-markdown__table tbody td:first-child .katex')
    expect(symbolCells.length).toBeGreaterThanOrEqual(2)

    const inlineSymbols = container.querySelectorAll('.engineering-math-inline .katex')
    expect(inlineSymbols.length).toBeGreaterThanOrEqual(1)
  })

  it('renders bold symbols in prose with KaTeX', () => {
    const { container } = render(<StandardsMarkdownViewer content={SAMPLE_BODY} />)

    expect(screen.getByText(/not less than/)).toBeInTheDocument()
    expect(container.querySelector('.standards-markdown__p .katex')).toBeTruthy()
  })

  it('keeps non-symbol inline code as monospace', () => {
    const { container } = render(
      <StandardsMarkdownViewer content="See node `B313-304.1.2` for details." />,
    )

    const inlineCode = container.querySelector('.standards-markdown__inline-code')
    expect(inlineCode).toBeTruthy()
    expect(inlineCode).toHaveTextContent('B313-304.1.2')
  })

  it('renders inequality expressions in prose with KaTeX', () => {
    const { container } = render(
      <StandardsMarkdownViewer content="exception, for pipe with Do/t < 10, the value of S to be used." />,
    )

    expect(container.querySelector('.standards-markdown__p .katex')).toBeTruthy()
  })

  it('renders node cross-reference links as standard reference controls', () => {
    render(
      <StandardsMarkdownViewer content="See [§304.1.2](node:B313-304.1.2) for internal pressure design." />,
    )

    const link = screen.getByRole('button', { name: '§304.1.2' })
    expect(link).toHaveClass('standard-reference-link__button')

    fireEvent.click(link)

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-B313-304.1.2')
  })

  it('renders table cross-reference links as table reference controls', () => {
    render(
      <StandardsMarkdownViewer content="Quality factor from [Table A-1A](table:A-1A)." />,
    )

    const link = screen.getByRole('button', { name: 'Table A-1A' })
    expect(link).toHaveClass('standard-reference-link__button')

    fireEvent.click(link)

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-A-1A')
  })

  it('treats legacy node:table_* links as table references', () => {
    render(
      <StandardsMarkdownViewer content="See [Table A-1A](node:table_b31_3_A-1A)." />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Table A-1A' }))

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-table_b31_3_A-1A')
  })

  it('renders external links with enhanced external-link styling', () => {
    render(
      <StandardsMarkdownViewer content="See [ASME B31.3](https://www.asme.org/codes-standards) for details." />,
    )

    const link = screen.getByRole('link', { name: /Opens external link: ASME B31\.3/i })
    expect(link).toHaveClass('external-link')
    expect(link).toHaveAttribute('href', 'https://www.asme.org/codes-standards')
    expect(link).toHaveAttribute('target', '_blank')
    expect(screen.getByText('External')).toHaveClass('external-link__badge')
  })
})
