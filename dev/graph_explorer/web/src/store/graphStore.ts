import { create } from 'zustand'
import type { Edge, Node } from '@xyflow/react'
import type {
  ExpansionEdge,
  ExpansionNode,
  ExpansionViewToggles,
  GraphAnalysis,
  GraphContext,
  GraphEdgeData,
  GraphNodeData,
  NodeDetail,
  WorkflowExpansionView,
} from '../types'
import { applyExpansionFilters } from '../utils/expansionFilters'
import { ALL_NODE_TYPES } from '../utils/nodeStyles'
import { layoutGraph, phaseRank } from '../utils/layout'
import { readTaskIdFromUrl } from '../utils/taskQuery'

interface GraphStoreState {
  revision: string
  expansionRevision: string
  taskId: string | null
  context: GraphContext | null
  expansionView: WorkflowExpansionView | null
  selectedExpansionNode: ExpansionNode | null
  viewToggles: ExpansionViewToggles
  rawNodes: GraphNodeData[]
  rawEdges: GraphEdgeData[]
  flowNodes: Node[]
  flowEdges: Edge[]
  positions: Record<string, { x: number; y: number }>
  selectedNodeId: string | null
  nodeDetail: NodeDetail | null
  searchQuery: string
  searchMatchIds: string[]
  visibleTypes: Set<string>
  analysis: GraphAnalysis | null
  connected: boolean
  setExpansionView: (view: WorkflowExpansionView) => void
  setViewToggle: (key: keyof ExpansionViewToggles, value: boolean) => void
  setSelectedExpansionNode: (node: ExpansionNode | null) => void
  setSnapshot: (nodes: GraphNodeData[], edges: GraphEdgeData[], context: GraphContext, revision: string) => void
  applyDelta: (payload: {
    revision: string
    added_nodes: GraphNodeData[]
    removed_nodes: string[]
    changed_nodes: GraphNodeData[]
    added_edges: GraphEdgeData[]
    removed_edges: string[]
  }) => void
  setSelectedNodeId: (id: string | null) => void
  setNodeDetail: (detail: NodeDetail | null) => void
  setSearchQuery: (query: string) => void
  setSearchMatchIds: (ids: string[]) => void
  toggleType: (nodeType: string) => void
  setAnalysis: (analysis: GraphAnalysis | null) => void
  setConnected: (connected: boolean) => void
  updatePositions: (nodes: Node[]) => void
  rebuildFlow: () => void
}

const defaultToggles: ExpansionViewToggles = {
  showSkipped: true,
  showFullGraph: false,
  showParameters: true,
  showReferenceEdges: false,
  autoRefresh: true,
}

function toExpansionFlowNodes(
  nodes: ExpansionNode[],
  positions: Record<string, { x: number; y: number }>,
  searchMatchIds: string[],
  selectedNodeId: string | null,
): Node[] {
  const matchSet = new Set(searchMatchIds)
  return nodes.map((node, index) => ({
    id: node.id,
    type: 'graphNode',
    position: positions[node.id] ?? { x: (index % 10) * 220, y: Math.floor(index / 10) * 90 },
    data: {
      label: node.label,
      nodeType: node.type,
      expansionStatus: node.status,
      reason: node.reason,
      phase: node.phase,
      description: node.reason,
      skipped: node.skipped,
      highlighted: matchSet.has(node.id),
      selected: selectedNodeId === node.id,
    },
  }))
}

function buildExpansionPhaseRanks(nodes: ExpansionNode[]): Record<string, number> {
  return Object.fromEntries(
    nodes.map((node) => [
      node.id,
      node.type === 'workflow' ? 0 : phaseRank(node.phase) + 1,
    ]),
  )
}

function toExpansionFlowEdges(edges: ExpansionEdge[], selectedNodeId: string | null): Edge[] {
  return edges.map((edge) => {
    const connected =
      selectedNodeId !== null && (edge.source === selectedNodeId || edge.target === selectedNodeId)
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'graphEdge',
      zIndex: connected ? 1000 : undefined,
      data: {
        edgeType: edge.type,
        condition: edge.condition,
        traversed: edge.active,
        skipped: edge.skipped,
        reason: edge.reason,
        highlighted: connected,
        dimmed: selectedNodeId !== null && !connected,
      },
      animated: edge.active && !edge.skipped,
    }
  })
}

function toFlowNodes(
  nodes: GraphNodeData[],
  positions: Record<string, { x: number; y: number }>,
  searchMatchIds: string[],
  selectedNodeId: string | null,
): Node[] {
  const matchSet = new Set(searchMatchIds)
  return nodes.map((node, index) => ({
    id: node.id,
    type: 'graphNode',
    position: positions[node.id] ?? { x: (index % 8) * 220, y: Math.floor(index / 8) * 90 },
    data: {
      label: node.name,
      nodeType: node.node_type,
      kind: typeof node.metadata?.kind === 'string' ? node.metadata.kind : null,
      display:
        node.metadata?.display && typeof node.metadata.display === 'object'
          ? (node.metadata.display as { color?: string; label?: string })
          : undefined,
      description: node.description,
      executionState:
        typeof node.metadata?.execution_state === 'string' ? node.metadata.execution_state : null,
      highlighted: matchSet.has(node.id),
      selected: selectedNodeId === node.id,
    },
  }))
}

function toFlowEdges(edges: GraphEdgeData[], selectedNodeId: string | null): Edge[] {
  return edges.map((edge) => {
    const connected =
      selectedNodeId !== null && (edge.source === selectedNodeId || edge.target === selectedNodeId)
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'graphEdge',
      zIndex: connected ? 1000 : undefined,
      data: {
        edgeType: edge.edge_type,
        traversed: edge.metadata?.traversed === true,
        highlighted: connected,
        dimmed: selectedNodeId !== null && !connected,
      },
      animated: edge.metadata?.traversed === true || edge.edge_type === 'next_step',
    }
  })
}

export const useGraphStore = create<GraphStoreState>((set, get) => ({
  revision: '',
  expansionRevision: '',
  taskId: readTaskIdFromUrl(),
  context: null,
  expansionView: null,
  selectedExpansionNode: null,
  viewToggles: defaultToggles,
  rawNodes: [],
  rawEdges: [],
  flowNodes: [],
  flowEdges: [],
  positions: {},
  selectedNodeId: null,
  nodeDetail: null,
  searchQuery: '',
  searchMatchIds: [],
  visibleTypes: new Set(ALL_NODE_TYPES),
  analysis: null,
  connected: false,

  setExpansionView: (view) => {
    const { positions, searchMatchIds, selectedNodeId, viewToggles } = get()
    const filtered = applyExpansionFilters(view.nodes, view.edges, viewToggles)
    const flowNodes = toExpansionFlowNodes(filtered.nodes, positions, searchMatchIds, selectedNodeId)
    const flowEdges = toExpansionFlowEdges(filtered.edges, selectedNodeId)
    const laidOut = layoutGraph(flowNodes, flowEdges, {
      rankByNodeId: buildExpansionPhaseRanks(filtered.nodes),
    })
    const newPositions = Object.fromEntries(laidOut.map((node) => [node.id, node.position]))
    set({
      expansionRevision: view.revision,
      expansionView: view,
      context: {
        task_id: view.task_id,
        workflow_id: view.workflow,
        session_id: 'default',
        node_count: filtered.nodes.length,
        edge_count: filtered.edges.length,
        message: view.warnings[0] ?? null,
      },
      flowNodes: laidOut,
      flowEdges,
      positions: newPositions,
    })
  },

  setViewToggle: (key, value) => {
    set({ viewToggles: { ...get().viewToggles, [key]: value } })
    const view = get().expansionView
    if (view) get().setExpansionView(view)
  },

  setSelectedExpansionNode: (node) => set({ selectedExpansionNode: node }),

  setSnapshot: (nodes, edges, context, revision) => {
    const { positions, searchMatchIds, selectedNodeId } = get()
    const flowNodes = toFlowNodes(nodes, positions, searchMatchIds, selectedNodeId)
    const flowEdges = toFlowEdges(edges, selectedNodeId)
    const laidOut = layoutGraph(flowNodes, flowEdges)
    const newPositions = Object.fromEntries(laidOut.map((node) => [node.id, node.position]))
    set({
      revision,
      context,
      rawNodes: nodes,
      rawEdges: edges,
      flowNodes: laidOut,
      flowEdges,
      positions: newPositions,
    })
    get().rebuildFlow()
  },

  applyDelta: (payload) => {
    const state = get()
    let nodes = [...state.rawNodes]
    let edges = [...state.rawEdges]
    let positions = { ...state.positions }

    const removeNodeSet = new Set(payload.removed_nodes)
    nodes = nodes.filter((node) => !removeNodeSet.has(node.id))
    for (const nodeId of payload.removed_nodes) {
      delete positions[nodeId]
    }

    for (const changed of payload.changed_nodes) {
      const idx = nodes.findIndex((node) => node.id === changed.id)
      if (idx >= 0) nodes[idx] = changed
    }

    const existingIds = new Set(nodes.map((node) => node.id))
    let addedIndex = nodes.length
    for (const added of payload.added_nodes) {
      if (!existingIds.has(added.id)) {
        nodes.push(added)
        if (!positions[added.id]) {
          positions[added.id] = {
            x: (addedIndex % 8) * 220,
            y: Math.floor(addedIndex / 8) * 90,
          }
          addedIndex += 1
        }
      }
    }

    const removeEdgeSet = new Set(payload.removed_edges)
    edges = edges.filter((edge) => !removeEdgeSet.has(edge.id))
    edges.push(...payload.added_edges)

    const context = state.context ?? {
      task_id: null,
      workflow_id: null,
      session_id: 'default',
      node_count: nodes.length,
      edge_count: edges.length,
    }

    set({
      revision: payload.revision,
      context: {
        ...context,
        node_count: nodes.length,
        edge_count: edges.length,
      },
      rawNodes: nodes,
      rawEdges: edges,
      positions,
    })
    get().rebuildFlow()
  },

  setSelectedNodeId: (id) => {
    set({ selectedNodeId: id })
    get().rebuildFlow()
  },

  setNodeDetail: (detail) => set({ nodeDetail: detail }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setSearchMatchIds: (ids) => {
    set({ searchMatchIds: ids })
    get().rebuildFlow()
  },

  toggleType: (nodeType) => {
    const next = new Set(get().visibleTypes)
    if (next.has(nodeType)) next.delete(nodeType)
    else next.add(nodeType)
    set({ visibleTypes: next })
    get().rebuildFlow()
  },

  setAnalysis: (analysis) => set({ analysis }),

  setConnected: (connected) => set({ connected }),

  updatePositions: (nodes) => {
    const positions = { ...get().positions }
    for (const node of nodes) {
      positions[node.id] = node.position
    }
    set({ positions, flowNodes: nodes })
  },

  rebuildFlow: () => {
    const state = get()
    if (state.expansionView) {
      state.setExpansionView(state.expansionView)
      return
    }
    const { rawNodes, rawEdges, positions, visibleTypes, searchMatchIds, selectedNodeId } = state
    const filteredNodes = rawNodes.filter((node) => visibleTypes.has(node.node_type))
    const visibleIds = new Set(filteredNodes.map((node) => node.id))
    const filteredEdges = rawEdges.filter(
      (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
    )
    const flowNodes = toFlowNodes(filteredNodes, positions, searchMatchIds, selectedNodeId)
    const flowEdges = toFlowEdges(filteredEdges, selectedNodeId)
    const laidOut = layoutGraph(flowNodes, flowEdges)
    const newPositions = Object.fromEntries(laidOut.map((node) => [node.id, node.position]))
    set({ flowNodes: laidOut, flowEdges, positions: newPositions })
  },
}))
