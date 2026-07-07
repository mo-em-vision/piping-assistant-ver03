import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { executionStateStyle, expansionNodeShapeClass, expansionStatusStyle, nodeStyle } from '../utils/nodeStyles'

interface GraphNodeData {
  label: string
  nodeType: string
  kind?: string | null
  display?: { color?: string; label?: string }
  description?: string
  executionState?: string | null
  expansionStatus?: string | null
  skipped?: boolean
  highlighted?: boolean
  selected?: boolean
}

function GraphNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as GraphNodeData
  const style = nodeStyle(nodeData.nodeType, nodeData.kind, nodeData.display)
  const expansionPalette = expansionStatusStyle(nodeData.expansionStatus)
  const executionPalette = executionStateStyle(nodeData.executionState)
  const palette = expansionPalette ?? executionPalette ?? { bg: style.bg, border: style.border }
  const className = [
    'graph-node',
    expansionNodeShapeClass(nodeData.nodeType),
    nodeData.highlighted ? 'highlighted' : '',
    nodeData.selected ? 'selected' : '',
    nodeData.skipped || nodeData.expansionStatus === 'skipped' ? 'is-skipped' : '',
    expansionPalette?.dashed ? 'is-dashed' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={className}
      style={{ background: palette.bg, borderColor: palette.border, color: '#f8fafc' }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="graph-node-title">{nodeData.label}</div>
      <div className="graph-node-type">{nodeData.expansionStatus ?? style.label}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

export default memo(GraphNodeComponent)
