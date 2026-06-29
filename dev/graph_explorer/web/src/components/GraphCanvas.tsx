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
}

export default function GraphCanvas({ onSelectNode, fitViewTrigger }: GraphCanvasProps) {
  const flowNodes = useGraphStore((s) => s.flowNodes)
  const flowEdges = useGraphStore((s) => s.flowEdges)
  const updatePositions = useGraphStore((s) => s.updatePositions)
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
    return (
      <div className="empty-state">
        <div>
          <p>{context?.message ?? 'No graph data available.'}</p>
          <p style={{ marginTop: 8 }}>
            Start the desktop app and create or activate an engineering task.
          </p>
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
      onNodeDragStop={onNodeDragStop}
      colorMode="dark"
      fitView
      minZoom={0.05}
      maxZoom={2}
      onlyRenderVisibleElements
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} color="#1e2533" />
      <Controls />
      <MiniMap nodeColor={minimapNodeColor} maskColor="rgba(15,17,23,0.75)" />
    </ReactFlow>
  )
}
