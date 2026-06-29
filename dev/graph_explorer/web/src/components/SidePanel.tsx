import type { NodeDetail } from '../types'

interface SidePanelProps {
  detail: NodeDetail | null
  onSelectPeer: (nodeId: string) => void
}

export default function SidePanel({ detail, onSelectPeer }: SidePanelProps) {
  if (!detail) {
    return (
      <div className="panel">
        <div className="section-title">Node detail</div>
        <p style={{ fontSize: 13, color: '#94a3b8' }}>Select a node to inspect its properties.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="section-title">Node detail</div>
      <h2 style={{ margin: '0 0 8px', fontSize: 16 }}>{detail.name}</h2>
      <p className="badge">{detail.node_type}</p>

      <div className="detail-section">
        <h3>ID</h3>
        <p>{detail.id}</p>
      </div>

      {detail.description && (
        <div className="detail-section">
          <h3>Description</h3>
          <p>{detail.description}</p>
        </div>
      )}

      <div className="detail-section">
        <h3>Inputs</h3>
        {detail.inputs.length ? (
          <ul>
            {detail.inputs.map((item) => (
              <li key={item}>
                <button type="button" className="peer-link" onClick={() => onSelectPeer(item)}>
                  {item}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>—</p>
        )}
      </div>

      <div className="detail-section">
        <h3>Outputs</h3>
        {detail.outputs.length ? (
          <ul>
            {detail.outputs.map((item) => (
              <li key={item}>
                <button type="button" className="peer-link" onClick={() => onSelectPeer(item)}>
                  {item}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>—</p>
        )}
      </div>

      <div className="detail-section">
        <h3>Incoming edges</h3>
        {detail.incoming_edges.length ? (
          <ul>
            {detail.incoming_edges.map((edge) => (
              <li key={`${edge.peer_id}-${edge.edge_type}`}>
                <span className="badge">{edge.edge_type}</span>{' '}
                <button type="button" className="peer-link" onClick={() => onSelectPeer(edge.peer_id)}>
                  {edge.peer_id}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>—</p>
        )}
      </div>

      <div className="detail-section">
        <h3>Outgoing edges</h3>
        {detail.outgoing_edges.length ? (
          <ul>
            {detail.outgoing_edges.map((edge) => (
              <li key={`${edge.peer_id}-${edge.edge_type}`}>
                <span className="badge">{edge.edge_type}</span>{' '}
                <button type="button" className="peer-link" onClick={() => onSelectPeer(edge.peer_id)}>
                  {edge.peer_id}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>—</p>
        )}
      </div>

      {detail.standard_refs.length > 0 && (
        <div className="detail-section">
          <h3>Standard references</h3>
          <ul>
            {detail.standard_refs.map((ref) => (
              <li key={ref}>{ref}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="detail-section">
        <h3>Metadata</h3>
        <pre
          style={{
            fontSize: 11,
            background: '#0f1117',
            padding: 8,
            borderRadius: 6,
            overflow: 'auto',
            maxHeight: 200,
          }}
        >
          {JSON.stringify(detail.metadata, null, 2)}
        </pre>
      </div>

      {detail.body_preview && (
        <div className="detail-section">
          <h3>Body</h3>
          <pre
            style={{
              fontSize: 11,
              background: '#0f1117',
              padding: 8,
              borderRadius: 6,
              overflow: 'auto',
              maxHeight: 160,
              whiteSpace: 'pre-wrap',
            }}
          >
            {detail.body_preview}
          </pre>
        </div>
      )}
    </div>
  )
}
