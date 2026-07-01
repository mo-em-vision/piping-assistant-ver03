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

  it('renders bare Obsidian-style display equations with equation tags', () => {
    const content = `**(a)** For t < D/6:

$$
 t = PD/2(SEW + PY)
\\tag{3a}
$$

$$
t = P(d+2c)/2(SEW - P(1-Y))
\\tag{3b}
$$

**(b)** For t >= D/6.`

    const { container } = render(<StandardsMarkdownViewer content={content} />)

    expect(container.querySelectorAll('.standards-markdown__equation .katex').length).toBe(2)
    expect(container.querySelectorAll('.katex .tag').length).toBeGreaterThanOrEqual(2)
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

  it('renders inline LaTeX fractions in paragraph prose', () => {
    const { container } = render(
      <StandardsMarkdownViewer content="**(a)** For $t < \\frac{D}{6}$, the internal pressure design thickness shall be calculated." />,
    )

    expect(container.querySelector('.standards-markdown__p .katex .mfrac, .standards-markdown__p .katex .frac-line')).toBeTruthy()
  })

  it('renders bare display equations containing \\frac', () => {
    const content = `**(a)** For t < D/6:

$$
 t = \\frac{PD}{2(SEW + PY)}
\\tag{3a}
$$

Following text.`

    const { container } = render(<StandardsMarkdownViewer content={content} />)

    expect(
      container.querySelectorAll('.standards-markdown__equation .katex .mfrac, .standards-markdown__equation .katex .frac-line').length,
    ).toBeGreaterThanOrEqual(1)
    expect(container.querySelector('.katex .tag')).toBeTruthy()
  })

  it('renders legacy slash display equations with equation tags', () => {
    const content = `**(a)** For t < D/6:

$$
 t = PD/2(SEW + PY)
\\tag{3a}
$$

Following text.`

    const { container } = render(<StandardsMarkdownViewer content={content} />)

    expect(
      container.querySelectorAll('.standards-markdown__equation .katex .mfrac, .standards-markdown__equation .katex .frac-line').length,
    ).toBeGreaterThanOrEqual(1)
    expect(container.querySelector('.katex .tag')).toBeTruthy()
  })

  it('renders paragraph and display blocks from LaTeX standards content', () => {
    const content = `**(a)** For $t < \\frac{D}{6}$, the internal pressure design thickness shall be calculated.

$$
 t = \\frac{PD}{2(SEW + PY)}
\\tag{3a}
$$

$$
t = \\frac{P(d+2c)}{2(SEW - P(1-Y))}
\\tag{3b}
$$`

    const { container } = render(<StandardsMarkdownViewer content={content} />)

    expect(container.querySelector('.standards-markdown__p .katex .frac-line')).toBeTruthy()
    expect(
      container.querySelectorAll('.standards-markdown__equation .katex .frac-line').length,
    ).toBeGreaterThanOrEqual(2)
    expect(container.querySelectorAll('.katex .tag').length).toBeGreaterThanOrEqual(2)
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
      <StandardsMarkdownViewer content="Quality factor from [Table A-2](table:asme_b31.3_A-2)." />,
    )

    const link = screen.getByRole('button', { name: 'Table A-2' })
    expect(link).toHaveClass('standard-reference-link__button')

    fireEvent.click(link)

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-asme_b31.3_A-2')
  })

  it('treats legacy node:table_* links as table references', () => {
    render(
      <StandardsMarkdownViewer content="See [Table A-2](node:table_b31_3_A-2)." />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Table A-2' }))

    expect(useRightPanelStore.getState().activeTabId).toBe('ref-table-table_b31_3_A-2')
  })

  it('renders node subsection cross-reference links as separate reference tabs', () => {
    render(
      <StandardsMarkdownViewer content="See [para. 302.3.5(e)](node:B313-302.3.5/e) for weld joint strength reduction." />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'para. 302.3.5(e)' }))

    const state = useRightPanelStore.getState()
    expect(state.activeTabId).toBe('ref-B313-302.3.5-e')
    const tab = state.tabs.find((item) => item.id === 'ref-B313-302.3.5-e')
    expect(tab?.kind).toBe('reference')
    if (tab?.kind === 'reference') {
      expect(tab.referenceId).toBe('B313-302.3.5')
      expect(tab.viewerContext).toEqual({ subsectionId: 'e' })
    }
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
