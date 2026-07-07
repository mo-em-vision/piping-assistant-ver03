import { describe, expect, it } from 'vitest'
import type { Edge, Node } from '@xyflow/react'

import { layoutGraph, phaseRank } from '@graph-explorer/utils/layout'

function makeNode(id: string): Node {
  return { id, type: 'graphNode', position: { x: 0, y: 0 }, data: { label: id } }
}

function makeEdge(source: string, target: string, edgeType?: string): Edge {
  return {
    id: `${source}->${target}`,
    source,
    target,
    type: 'graphEdge',
    data: edgeType ? { edgeType } : undefined,
  }
}

describe('layoutGraph', () => {
  it('orders expansion phases left to right', () => {
    const nodes = [makeNode('early'), makeNode('late')]
    const edges = [makeEdge('early', 'late', 'active')]
    const laidOut = layoutGraph(nodes, edges, {
      rankByNodeId: { early: 1, late: 4 },
    })

    const early = laidOut.find((node) => node.id === 'early')!
    const late = laidOut.find((node) => node.id === 'late')!
    expect(early.position.x).toBeLessThan(late.position.x)
  })

  it('ignores reference edges when computing layout', () => {
    const nodes = [makeNode('a'), makeNode('b'), makeNode('c')]
    const edges = [
      makeEdge('a', 'b', 'active'),
      makeEdge('c', 'a', 'reference'),
    ]
    const laidOut = layoutGraph(nodes, edges, {
      rankByNodeId: { a: 1, b: 2, c: 0 },
    })

    const a = laidOut.find((node) => node.id === 'a')!
    const b = laidOut.find((node) => node.id === 'b')!
    expect(a.position.x).toBeLessThan(b.position.x)
  })
})

describe('phaseRank', () => {
  it('returns stable ordering for known phases', () => {
    expect(phaseRank('expansion_assumptions')).toBeLessThan(phaseRank('path_decisions'))
    expect(phaseRank('path_decisions')).toBeLessThan(phaseRank('parameter_gathering'))
  })
})
