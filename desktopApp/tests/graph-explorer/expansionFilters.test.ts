import { describe, expect, it } from 'vitest'

import {
  applyExpansionFilters,
  filterExpansionEdges,
  filterExpansionNodes,
} from '@graph-explorer/utils/expansionFilters'
import type { ExpansionEdge, ExpansionNode } from '@graph-explorer/types'

const nodes: ExpansionNode[] = [
  {
    id: '304.1.1-a',
    label: '§304.1.1',
    type: 'definition',
    status: 'expanded',
    visible: true,
    active: true,
    blocked: false,
    skipped: false,
    reason: 'definition',
    missing_inputs: [],
    provided_outputs: [],
    required_inputs: [],
    phase: 'expansion_assumptions',
    details: {},
  },
  {
    id: '304.1.3',
    label: '§304.1.3',
    type: 'definition',
    status: 'skipped',
    visible: true,
    active: false,
    blocked: false,
    skipped: true,
    reason: 'pressure_loading != external_pressure',
    missing_inputs: [],
    provided_outputs: [],
    required_inputs: [],
    phase: 'path_decisions',
    details: {},
  },
  {
    id: 'PARAM-internal-design-gage-pressure',
    label: 'internal_design_gage_pressure',
    type: 'parameter',
    status: 'awaiting_input',
    visible: false,
    active: false,
    blocked: true,
    skipped: false,
    reason: 'hidden parameter',
    missing_inputs: ['internal_design_gage_pressure'],
    provided_outputs: [],
    required_inputs: ['internal_design_gage_pressure'],
    phase: 'parameter_gathering',
    details: {},
  },
]

const edges: ExpansionEdge[] = [
  {
    id: '304.1.1-a->304.1.2-a',
    source: '304.1.1-a',
    target: '304.1.2-a',
    type: 'conditional',
    active: true,
    skipped: false,
    reason: 'internal branch',
    condition: 'pressure_loading == internal_pressure',
  },
  {
    id: '304.1.1-a->304.1.3',
    source: '304.1.1-a',
    target: '304.1.3',
    type: 'skipped',
    active: false,
    skipped: true,
    reason: 'skipped branch',
    condition: 'pressure_loading == external_pressure',
  },
  {
    id: '304.1.1-a->ref',
    source: '304.1.1-a',
    target: 'ref-node',
    type: 'reference',
    active: false,
    skipped: false,
    reason: 'reference',
    condition: '',
  },
]

describe('expansionFilters', () => {
  it('hides skipped nodes when showSkipped is false', () => {
    const filtered = filterExpansionNodes(nodes, {
      showSkipped: false,
      showFullGraph: false,
      showParameters: true,
      showReferenceEdges: false,
      autoRefresh: true,
    })
    expect(filtered.map((node) => node.id)).toEqual(['304.1.1-a'])
  })

  it('shows full graph nodes when enabled', () => {
    const filtered = filterExpansionNodes(nodes, {
      showSkipped: true,
      showFullGraph: true,
      showParameters: true,
      showReferenceEdges: false,
      autoRefresh: true,
    })
    expect(filtered.map((node) => node.id)).toContain('PARAM-internal-design-gage-pressure')
  })

  it('filters reference edges unless enabled', () => {
    const visible = new Set(['304.1.1-a', '304.1.3', '304.1.2-a', 'ref-node'])
    const withoutReference = filterExpansionEdges(edges, visible, {
      showSkipped: true,
      showFullGraph: false,
      showParameters: true,
      showReferenceEdges: false,
      autoRefresh: true,
    })
    expect(withoutReference.some((edge) => edge.type === 'reference')).toBe(false)

    const withReference = filterExpansionEdges(edges, visible, {
      showSkipped: true,
      showFullGraph: false,
      showParameters: true,
      showReferenceEdges: true,
      autoRefresh: true,
    })
    expect(withReference.some((edge) => edge.type === 'reference')).toBe(true)
  })

  it('applyExpansionFilters returns paired nodes and edges', () => {
    const result = applyExpansionFilters(nodes, edges, {
      showSkipped: true,
      showFullGraph: false,
      showParameters: false,
      showReferenceEdges: false,
      autoRefresh: true,
    })
    expect(result.nodes.map((node) => node.id)).toEqual(['304.1.1-a', '304.1.3'])
    expect(result.edges.length).toBeGreaterThan(0)
  })
})
