import type { StandardsBrowseNodeDto } from '@/types/backend/api'

export function nodeMatchesSearch(node: StandardsBrowseNodeDto, query: string): boolean {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    return true
  }
  const haystack = [
    node.label,
    node.node_id ?? '',
    node.workflow_id ?? '',
    node.description ?? '',
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(normalized)
}

export function filterBrowseTree(
  nodes: StandardsBrowseNodeDto[],
  query: string,
): StandardsBrowseNodeDto[] {
  const normalized = query.trim()
  if (!normalized) {
    return nodes
  }

  const filtered: StandardsBrowseNodeDto[] = []
  for (const node of nodes) {
    if (node.kind === 'group') {
      const children = filterBrowseTree(node.children ?? [], normalized)
      if (children.length > 0 || nodeMatchesSearch(node, normalized)) {
        filtered.push({
          ...node,
          children: children.length > 0 ? children : node.children,
        })
      }
      continue
    }

    if (nodeMatchesSearch(node, normalized)) {
      filtered.push(node)
    }
  }
  return filtered
}

export function isSelectableBrowseNode(node: StandardsBrowseNodeDto): boolean {
  return (
    node.kind === 'group' ||
    node.kind === 'node' ||
    node.kind === 'table' ||
    node.kind === 'workflow'
  )
}

export type BrowseIndexEntry = {
  node: StandardsBrowseNodeDto
  depth: number
}

export function collectBrowseIndexEntries(group: StandardsBrowseNodeDto): BrowseIndexEntry[] {
  const entries: BrowseIndexEntry[] = []

  const walk = (nodes: StandardsBrowseNodeDto[], depth: number) => {
    for (const node of nodes) {
      if (node.kind === 'group') {
        entries.push({ node, depth })
        walk(node.children ?? [], depth + 1)
        continue
      }
      if (node.kind === 'node' || node.kind === 'table' || node.kind === 'workflow') {
        entries.push({ node, depth })
      }
    }
  }

  walk(group.children ?? [], 0)
  return entries
}
