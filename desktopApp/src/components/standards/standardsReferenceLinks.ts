import type { StandardsReferenceKind } from '@/store/rightPanelStore'

const NODE_LINK_PREFIX = 'node:'
const TABLE_LINK_PREFIX = 'table:'

export interface StandardsReferenceTarget {
  referenceKind: StandardsReferenceKind
  referenceId: string
}

export function parseStandardsReferenceHref(href?: string): StandardsReferenceTarget | null {
  if (href?.startsWith(TABLE_LINK_PREFIX)) {
    const referenceId = href.slice(TABLE_LINK_PREFIX.length).trim()
    return referenceId ? { referenceKind: 'table', referenceId } : null
  }

  if (href?.startsWith(NODE_LINK_PREFIX)) {
    const referenceId = href.slice(NODE_LINK_PREFIX.length).trim()
    if (!referenceId) {
      return null
    }
    if (referenceId.startsWith('table_')) {
      return { referenceKind: 'table', referenceId }
    }
    return { referenceKind: 'node', referenceId }
  }

  return null
}

export function standardsUrlTransform(url: string, defaultTransform: (value: string) => string): string {
  if (url.startsWith(NODE_LINK_PREFIX) || url.startsWith(TABLE_LINK_PREFIX)) {
    return url
  }
  return defaultTransform(url)
}
