import { memo } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  MarkerType,
  getSmoothStepPath,
  type EdgeProps,
} from '@xyflow/react'
import { edgeColor } from '../utils/nodeStyles'

interface GraphEdgeData {
  edgeType: string
  condition?: string
  traversed?: boolean
  skipped?: boolean
  reason?: string
  highlighted?: boolean
  dimmed?: boolean
}

function edgeStroke(
  edgeData: GraphEdgeData,
): { color: string; width: number; dash?: string; opacity?: number } {
  if (edgeData.highlighted) {
    return { color: '#fbbf24', width: 3, opacity: 1 }
  }
  if (edgeData.dimmed) {
    return { color: '#475569', width: 1, opacity: 0.2 }
  }
  if (edgeData.skipped || edgeData.edgeType === 'skipped') {
    return { color: '#737373', width: 1.5, dash: '6 4' }
  }
  if (edgeData.edgeType === 'reference') {
    return { color: '#94a3b8', width: 1.2, dash: '2 4' }
  }
  if (edgeData.edgeType === 'conditional') {
    return { color: '#38bdf8', width: 2, dash: edgeData.traversed ? undefined : '4 3' }
  }
  if (edgeData.edgeType === 'blocked') {
    return { color: '#fb923c', width: 1.8, dash: '5 3' }
  }
  const color = edgeColor(edgeData.edgeType)
  return { color, width: edgeData.traversed ? 2.5 : 1.5 }
}

function GraphEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const edgeData = (data ?? {}) as unknown as GraphEdgeData
  const stroke = edgeStroke(edgeData)
  const label = edgeData.condition || edgeData.edgeType
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 12,
  })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={{
          type: MarkerType.ArrowClosed,
          width: 18,
          height: 18,
          color: stroke.color,
        }}
        style={{
          stroke: stroke.color,
          strokeWidth: stroke.width,
          strokeDasharray: stroke.dash,
          opacity: stroke.opacity,
          animation:
            edgeData.traversed && !edgeData.highlighted
              ? 'graph-edge-flow 1.2s linear infinite'
              : undefined,
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              fontSize: 9,
              color: stroke.color,
              pointerEvents: 'none',
              background: 'rgba(15,17,23,0.85)',
              padding: '1px 4px',
              borderRadius: 3,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

export default memo(GraphEdgeComponent)
