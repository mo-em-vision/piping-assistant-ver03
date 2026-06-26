import { describe, expect, it } from 'vitest'

import { getSelectedText, isSelectionAskAiEligible } from '@/utils/centerPanelSelection'

function createSelection(container: HTMLElement, text: string, target: Node): Selection {
  const range = document.createRange()
  range.selectNodeContents(target)

  return {
    isCollapsed: false,
    rangeCount: 1,
    toString: () => text,
    getRangeAt: () => range,
    anchorNode: target,
    focusNode: target,
    containsNode: () => true,
  } as unknown as Selection
}

describe('centerPanelSelection', () => {
  it('returns trimmed selected text', () => {
    const selection = {
      isCollapsed: false,
      toString: () => '  hello  ',
    } as Selection

    expect(getSelectedText(selection)).toBe('hello')
  })

  it('returns null for collapsed or empty selection', () => {
    expect(getSelectedText({ isCollapsed: true, toString: () => '' } as Selection)).toBeNull()
    expect(getSelectedText({ isCollapsed: false, toString: () => '   ' } as Selection)).toBeNull()
  })

  it('allows selection inside panel history', () => {
    const container = document.createElement('main')
    const history = document.createElement('div')
    const paragraph = document.createElement('p')
    paragraph.textContent = 't = 12.5 mm'
    history.appendChild(paragraph)
    container.appendChild(history)

    const selection = createSelection(container, 't = 12.5 mm', paragraph)
    expect(isSelectionAskAiEligible(container, selection)).toBe(true)
  })

  it('rejects selection inside composer', () => {
    const container = document.createElement('main')
    const composer = document.createElement('div')
    composer.className = 'workflow-panel__composer'
    const input = document.createElement('input')
    input.value = 'typed value'
    composer.appendChild(input)
    container.appendChild(composer)

    const selection = createSelection(container, 'typed value', input)
    expect(isSelectionAskAiEligible(container, selection)).toBe(false)
  })

  it('rejects selection outside container', () => {
    const container = document.createElement('main')
    const outside = document.createElement('p')
    outside.textContent = 'outside'
    document.body.appendChild(outside)

    const selection = createSelection(container, 'outside', outside)
    expect(isSelectionAskAiEligible(container, selection)).toBe(false)

    outside.remove()
  })
})
