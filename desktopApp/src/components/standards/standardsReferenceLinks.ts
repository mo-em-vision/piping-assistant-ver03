import type { StandardsReferenceKind } from '@/store/rightPanelStore'

const NODE_LINK_PREFIX = 'node:'
const TABLE_LINK_PREFIX = 'table:'

export interface StandardsReferenceTarget {
  referenceKind: StandardsReferenceKind
  referenceId: string
  subsectionId?: string
}

function parseNodeReference(referenceId: string): StandardsReferenceTarget | null {
  if (!referenceId) {
    return null
  }
  if (referenceId.startsWith('table_')) {
    return { referenceKind: 'table', referenceId }
  }

  const slashIndex = referenceId.indexOf('/')
  if (slashIndex > 0) {
    const nodeId = referenceId.slice(0, slashIndex).trim()
    const subsectionId = referenceId.slice(slashIndex + 1).trim()
    if (nodeId && subsectionId) {
      return { referenceKind: 'node', referenceId: nodeId, subsectionId }
    }
  }

  return { referenceKind: 'node', referenceId }
}

export function parseStandardsReferenceHref(href?: string): StandardsReferenceTarget | null {
  if (href?.startsWith(TABLE_LINK_PREFIX)) {
    const referenceId = href.slice(TABLE_LINK_PREFIX.length).trim()
    return referenceId ? { referenceKind: 'table', referenceId } : null
  }

  if (href?.startsWith(NODE_LINK_PREFIX)) {
    const referenceId = href.slice(NODE_LINK_PREFIX.length).trim()
    return parseNodeReference(referenceId)
  }

  return null
}

export function standardsUrlTransform(url: string, defaultTransform: (value: string) => string): string {
  if (url.startsWith(NODE_LINK_PREFIX) || url.startsWith(TABLE_LINK_PREFIX)) {
    return url
  }
  return defaultTransform(url)
}
