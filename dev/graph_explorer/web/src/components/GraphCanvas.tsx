import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type Node,
  type OnNodeDrag,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useCallback, useEffect, useMemo, type MouseEvent } from 'react'
import GraphNodeComponent from './GraphNode'
import GraphEdgeComponent from './GraphEdge'
import { useGraphStore } from '../store/graphStore'
import { nodeStyle } from '../utils/nodeStyles'

const nodeTypes = { graphNode: GraphNodeComponent }
const edgeTypes = { graphEdge: GraphEdgeComponent }

interface GraphCanvasProps {
  onSelectNode: (nodeId: string) => void
  fitViewTrigger: number
  colorMode?: 'light' | 'dark'
}

export default function GraphCanvas({
  onSelectNode,
  fitViewTrigger,
  colorMode = 'dark',
}: GraphCanvasProps) {
  const flowNodes = useGraphStore((s) => s.flowNodes)
  const flowEdges = useGraphStore((s) => s.flowEdges)
  const updatePositions = useGraphStore((s) => s.updatePositions)
  const setSelectedNodeId = useGraphStore((s) => s.setSelectedNodeId)
  const setSelectedExpansionNode = useGraphStore((s) => s.setSelectedExpansionNode)
  const context = useGraphStore((s) => s.context)
  const { fitView } = useReactFlow()

  useEffect(() => {
    if (fitViewTrigger > 0 && flowNodes.length > 0) {
      fitView({ padding: 0.15, duration: 300 })
    }
  }, [fitViewTrigger, fitView, flowNodes.length])

  const onNodeClick = useCallback(
    (_event: MouseEvent, node: Node) => {
      onSelectNode(node.id)
    },
    [onSelectNode],
  )

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
    setSelectedExpansionNode(null)
  }, [setSelectedExpansionNode, setSelectedNodeId])

  const onNodeDragStop = useCallback<OnNodeDrag>(
    (_event, node) => {
      const current = useGraphStore.getState().flowNodes
      updatePositions(
        current.map((item) => (item.id === node.id ? { ...item, position: node.position } : item)),
      )
    },
    [updatePositions],
  )

  const minimapNodeColor = useMemo(
    () => (node: Node) => {
      const data = node.data as {
        nodeType?: string
        kind?: string | null
        display?: { color?: string; label?: string }
      }
      return nodeStyle(data.nodeType ?? 'unknown', data.kind, data.display).border
    },
    [],
  )

  if (!context?.node_count) {
    const title = context?.message ?? 'No graph data available.'
    const detail = !context
      ? 'Start the graph explorer backend and ensure the desktop app has an active task.'
      : context.message
        ? null
        : 'Run the workflow or submit inputs to expand the graph.'

    return (
      <div className="empty-state">
        <div>
          <p className="empty-state__title">{title}</p>
          {detail ? <p className="empty-state__detail">{detail}</p> : null}
          {context ? (
            <p className="empty-state__meta">
              Project: <strong>{context.session_id}</strong>
              {' · '}
              Task: <strong>{context.task_id ?? 'none'}</strong>
            </p>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={flowNodes}
      edges={flowEdges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      onNodeDragStop={onNodeDragStop}
      colorMode={colorMode}
      fitView
      minZoom={0.05}
      maxZoom={2}
      onlyRenderVisibleElements
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} color={colorMode === 'light' ? '#e2e8f0' : '#1e2533'} />
      <Controls />
      <MiniMap nodeColor={minimapNodeColor} maskColor="rgba(15,17,23,0.75)" />
    </ReactFlow>
  )
}
