import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { executionStateStyle, nodeStyle } from '../utils/nodeStyles'

interface GraphNodeData {
  label: string
  nodeType: string
  kind?: string | null
  display?: { color?: string; label?: string }
  description?: string
  executionState?: string | null
  highlighted?: boolean
  selected?: boolean
}

function GraphNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as GraphNodeData
  const style = nodeStyle(nodeData.nodeType, nodeData.kind, nodeData.display)
  const executionPalette = executionStateStyle(nodeData.executionState)
  const palette = executionPalette ?? { bg: style.bg, border: style.border }
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
      style={{ background: palette.bg, borderColor: palette.border, color: '#f8fafc' }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="graph-node-title">{nodeData.label}</div>
      <div className="graph-node-type">{style.label}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

export default memo(GraphNodeComponent)
