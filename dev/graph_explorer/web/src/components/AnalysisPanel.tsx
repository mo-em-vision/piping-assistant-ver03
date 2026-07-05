import type { GraphAnalysis } from '../types'

interface AnalysisPanelProps {
  analysis: GraphAnalysis | null
  onSelectNode: (nodeId: string) => void
}

function NodeList({
  title,
  nodeIds,
  onSelectNode,
}: {
  title: string
  nodeIds: string[]
  onSelectNode: (nodeId: string) => void
}) {
  if (!nodeIds.length) return null
  return (
    <div className="detail-section">
      <h3>{title} ({nodeIds.length})</h3>
      {nodeIds.map((nodeId) => (
        <div key={nodeId} className="analysis-item" onClick={() => onSelectNode(nodeId)}>
          {nodeId}
        </div>
      ))}
    </div>
  )
}

export default function AnalysisPanel({ analysis, onSelectNode }: AnalysisPanelProps) {
  if (!analysis) {
    return (
      <div className="detail-section">
        <div className="section-title">Graph analysis</div>
        <p style={{ fontSize: 13, color: '#94a3b8' }}>Loading analysis…</p>
      </div>
    )
  }

  return (
    <div>
      <div className="section-title">Graph analysis</div>
      <NodeList title="Orphans" nodeIds={analysis.orphan_nodes} onSelectNode={onSelectNode} />
      <NodeList title="No incoming" nodeIds={analysis.no_incoming} onSelectNode={onSelectNode} />
      <NodeList title="No outgoing" nodeIds={analysis.no_outgoing} onSelectNode={onSelectNode} />

      {analysis.highly_connected.length > 0 && (
        <div className="detail-section">
          <h3>Highly connected</h3>
          {analysis.highly_connected.map((item) => (
            <div
              key={item.node_id}
              className="analysis-item"
              onClick={() => onSelectNode(item.node_id)}
            >
              {item.node_id} (in: {item.in_degree}, out: {item.out_degree})
            </div>
          ))}
        </div>
      )}

      {Object.keys(analysis.duplicate_names).length > 0 && (
        <div className="detail-section">
          <h3>Duplicate names</h3>
          {Object.entries(analysis.duplicate_names).map(([name, ids]) => (
            <div key={name}>
              <strong>{name}</strong>
              {ids.map((nodeId) => (
                <div key={nodeId} className="analysis-item" onClick={() => onSelectNode(nodeId)}>
                  {nodeId}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {analysis.cycles.length > 0 && (
        <div className="detail-section">
          <h3>Cycles ({analysis.cycles.length})</h3>
          {analysis.cycles.map((cycle, index) => (
            <div key={index} style={{ fontSize: 12, marginBottom: 6 }}>
              {cycle.map((nodeId, nodeIndex) => (
                <span key={`${index}-${nodeId}-${nodeIndex}`}>
                  {nodeIndex > 0 ? ' → ' : null}
                  <button
                    type="button"
                    className="analysis-item analysis-item--inline"
                    onClick={() => onSelectNode(nodeId)}
                  >
                    {nodeId}
                  </button>
                </span>
              ))}
            </div>
          ))}
        </div>
      )}

      {analysis.disconnected_components.length > 1 && (
        <div className="detail-section">
          <h3>Disconnected components ({analysis.disconnected_components.length})</h3>
          {analysis.disconnected_components.map((component, index) => (
            <div key={index} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>
                Component {index + 1} ({component.length} nodes)
              </div>
              {component.map((nodeId) => (
                <div key={nodeId} className="analysis-item" onClick={() => onSelectNode(nodeId)}>
                  {nodeId}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
