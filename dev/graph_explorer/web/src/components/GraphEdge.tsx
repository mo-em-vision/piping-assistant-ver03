import { memo } from 'react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'
import { edgeColor } from '../utils/nodeStyles'

interface GraphEdgeData {
  edgeType: string
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
  const color = edgeColor(edgeData.edgeType ?? 'default')
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{ stroke: color, strokeWidth: 1.5 }} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            fontSize: 9,
            color,
            pointerEvents: 'none',
            background: 'rgba(15,17,23,0.85)',
            padding: '1px 4px',
            borderRadius: 3,
          }}
        >
          {edgeData.edgeType}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export default memo(GraphEdgeComponent)
