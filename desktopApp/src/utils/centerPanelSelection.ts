export function getSelectedText(selection: Selection | null): string | null {
  if (!selection || selection.isCollapsed) {
    return null
  }

  const text = selection.toString().trim()
  return text.length > 0 ? text : null
}

function getRangeContainer(range: Range): Node {
  const node = range.commonAncestorContainer
  return node.nodeType === Node.TEXT_NODE ? node.parentNode ?? node : node
}

export function isSelectionAskAiEligible(
  container: HTMLElement,
  selection: Selection | null,
  composerSelector = '.workflow-panel__composer',
): boolean {
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
    return false
  }

  const text = getSelectedText(selection)
  if (!text) {
    return false
  }

  const range = selection.getRangeAt(0)
  const ancestor = getRangeContainer(range)
  if (!(ancestor instanceof Node) || !container.contains(ancestor)) {
    return false
  }

  const composer = container.querySelector(composerSelector)
  if (composer?.contains(ancestor)) {
    return false
  }

  return true
}
