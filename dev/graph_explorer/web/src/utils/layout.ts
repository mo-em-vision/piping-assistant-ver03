import dagre from 'dagre'
import type { Edge, Node } from '@xyflow/react'

const NODE_WIDTH = 200
const NODE_HEIGHT = 56

/** Workflow expansion phases in left-to-right unfold order. */
export const EXPANSION_PHASE_ORDER = [
  'expansion_assumptions',
  'path_decisions',
  'parameter_gathering',
  'coefficient_resolution',
  'execution_assumptions',
  'definition_equation_completion',
] as const

const LAYOUT_EDGE_TYPES_EXCLUDED = new Set(['reference', 'related_to', 'cites'])

export function phaseRank(phase: string): number {
  const index = EXPANSION_PHASE_ORDER.indexOf(phase as (typeof EXPANSION_PHASE_ORDER)[number])
  return index >= 0 ? index : EXPANSION_PHASE_ORDER.length
}

export interface LayoutGraphOptions {
  /** Pin nodes to dagre ranks so earlier phases sit further left. */
  rankByNodeId?: Record<string, number>
}

function edgeType(edge: Edge): string | undefined {
  const data = edge.data as { edgeType?: string } | undefined
  return data?.edgeType
}

function isLayoutEdge(edge: Edge): boolean {
  const type = edgeType(edge)
  return !type || !LAYOUT_EDGE_TYPES_EXCLUDED.has(type)
}

export function layoutGraph(nodes: Node[], edges: Edge[], options: LayoutGraphOptions = {}): Node[] {
  if (nodes.length === 0) return nodes

  const layoutEdges = edges.filter(isLayoutEdge)
  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: 'LR', align: 'UL', nodesep: 80, ranksep: 140, edgesep: 40 })

  for (const node of nodes) {
    const rank = options.rankByNodeId?.[node.id]
    const label: { width: number; height: number; minRank?: number; maxRank?: number } = {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    }
    if (rank !== undefined) {
      label.minRank = rank
      label.maxRank = rank
    }
    graph.setNode(node.id, label)
  }

  for (const edge of layoutEdges) {
    graph.setEdge(edge.source, edge.target)
  }

  dagre.layout(graph)

  return nodes.map((node) => {
    const position = graph.node(node.id)
    return {
      ...node,
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - NODE_HEIGHT / 2,
      },
    }
  })
}
