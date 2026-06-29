import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { nodeStyle } from '../utils/nodeStyles'

interface GraphNodeData {
  label: string
  nodeType: string
  kind?: string | null
  display?: { color?: string; label?: string }
  description?: string
  highlighted?: boolean
  selected?: boolean
}

function GraphNodeComponent({ data }: NodeProps) {
  const nodeData = data as GraphNodeData
  const style = nodeStyle(nodeData.nodeType, nodeData.kind, nodeData.display)
  const className = [
    'graph-node',
    nodeData.highlighted ? 'highlighted' : '',
    nodeData.selected ? 'selected' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={className}
      style={{ background: style.bg, borderColor: style.border, color: '#f8fafc' }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="graph-node-title">{nodeData.label}</div>
      <div className="graph-node-type">{style.label}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

export default memo(GraphNodeComponent)
