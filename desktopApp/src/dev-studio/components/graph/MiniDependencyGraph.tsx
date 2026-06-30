import type { RelationshipsPayload } from '@/dev-studio/api/devStudioApi'

interface MiniDependencyGraphProps {
  nodeId: string
  relationships: RelationshipsPayload
  onSelectNode: (id: string) => void
}

interface GraphNode {
  id: string
  x: number
  y: number
  direction: 'center' | 'incoming' | 'outgoing'
}

export function MiniDependencyGraph({ nodeId, relationships, onSelectNode }: MiniDependencyGraphProps) {
  const width = 280
  const height = 200
  const cx = width / 2
  const cy = height / 2

  const incomingIds = [
    ...new Set(
      Object.values(relationships.incoming).flatMap((items) => items.map((item) => item.id)),
    ),
  ]
  const outgoingIds = [
    ...new Set(
      Object.values(relationships.outgoing).flatMap((items) => items.map((item) => item.id)),
    ),
  ]

  const nodes: GraphNode[] = [{ id: nodeId, x: cx, y: cy, direction: 'center' }]

  incomingIds.slice(0, 6).forEach((id, index) => {
    const angle = Math.PI + (index - (incomingIds.length - 1) / 2) * 0.5
    nodes.push({
      id,
      x: cx + Math.cos(angle) * 90,
      y: cy + Math.sin(angle) * 70,
      direction: 'incoming',
    })
  })

  outgoingIds.slice(0, 6).forEach((id, index) => {
    const angle = (index - (outgoingIds.length - 1) / 2) * 0.5
    nodes.push({
      id,
      x: cx + Math.cos(angle) * 90,
      y: cy + Math.sin(angle) * 70,
      direction: 'outgoing',
    })
  })

  const nodeById = new Map(nodes.map((n) => [n.id, n]))

  const edges: Array<{ from: GraphNode; to: GraphNode }> = []
  for (const id of incomingIds.slice(0, 6)) {
    const from = nodeById.get(id)
    const to = nodeById.get(nodeId)
    if (from && to) edges.push({ from, to })
  }
  for (const id of outgoingIds.slice(0, 6)) {
    const from = nodeById.get(nodeId)
    const to = nodeById.get(id)
    if (from && to) edges.push({ from, to })
  }

  return (
    <div className="dev-studio__graph-section">
      <h3>Dependency graph</h3>
      <svg width={width} height={height} style={{ display: 'block', margin: '0 auto' }}>
        {edges.map(({ from, to }) => (
          <line
            key={`${from.id}-${to.id}`}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke="#3c3c3c"
            strokeWidth={1}
          />
        ))}
        {nodes.map((node) => (
          <g
            key={node.id}
            onClick={() => node.id !== nodeId && onSelectNode(node.id)}
            style={{ cursor: node.id === nodeId ? 'default' : 'pointer' }}
          >
            <circle
              cx={node.x}
              cy={node.y}
              r={node.direction === 'center' ? 10 : 7}
              fill={
                node.direction === 'center'
                  ? '#0078d4'
                  : node.direction === 'incoming'
                    ? '#4ec9b0'
                    : '#ce9178'
              }
            />
            <text
              x={node.x}
              y={node.y + (node.direction === 'center' ? 22 : 18)}
              textAnchor="middle"
              fill="#858585"
              fontSize={9}
            >
              {node.id.length > 14 ? `${node.id.slice(0, 12)}…` : node.id}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
