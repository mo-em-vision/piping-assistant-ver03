import type { ExpansionEdge, ExpansionNode, ExpansionViewToggles } from '../types'

export function filterExpansionNodes(
  nodes: ExpansionNode[],
  toggles: ExpansionViewToggles,
): ExpansionNode[] {
  return nodes.filter((node) => {
    if (!toggles.showFullGraph && !node.visible) return false
    if (!toggles.showSkipped && node.skipped) return false
    if (!toggles.showParameters && node.type === 'parameter') return false
    if (node.status === 'hidden') return false
    return true
  })
}

export function filterExpansionEdges(
  edges: ExpansionEdge[],
  visibleNodeIds: Set<string>,
  toggles: ExpansionViewToggles,
): ExpansionEdge[] {
  return edges.filter((edge) => {
    if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return false
    if (!toggles.showReferenceEdges && edge.type === 'reference') return false
    if (!toggles.showSkipped && edge.skipped) return false
    return true
  })
}

export function applyExpansionFilters(
  nodes: ExpansionNode[],
  edges: ExpansionEdge[],
  toggles: ExpansionViewToggles,
): { nodes: ExpansionNode[]; edges: ExpansionEdge[] } {
  const filteredNodes = filterExpansionNodes(nodes, toggles)
  const visibleIds = new Set(filteredNodes.map((node) => node.id))
  const filteredEdges = filterExpansionEdges(edges, visibleIds, toggles)
  return { nodes: filteredNodes, edges: filteredEdges }
}
