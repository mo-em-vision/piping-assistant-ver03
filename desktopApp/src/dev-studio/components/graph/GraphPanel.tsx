import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

import { MiniDependencyGraph } from './MiniDependencyGraph'

export function GraphPanel() {
  const relationships = useDevStudioStore((s) => s.relationships)
  const selectedId = useDevStudioStore((s) => s.selectedId)
  const loadNode = useDevStudioStore((s) => s.loadNode)

  if (!relationships || !selectedId) {
    return <div className="dev-studio__empty">Select a node to view graph context.</div>
  }

  const renderGroup = (title: string, grouped: Record<string, Array<{ id: string; type: string }>>) => (
    <div className="dev-studio__graph-section">
      <h3>{title}</h3>
      {Object.keys(grouped).length === 0 && <div className="dev-studio__list-item-meta">None</div>}
      {Object.entries(grouped).map(([edgeType, items]) => (
        <div key={edgeType} style={{ marginBottom: 8 }}>
          <div className="dev-studio__list-item-meta">{edgeType}</div>
          {items.map((item) => (
            <button
              key={`${edgeType}-${item.id}`}
              type="button"
              className="dev-studio__link"
              style={{ display: 'block', margin: '2px 0' }}
              onClick={() => void loadNode(item.id)}
            >
              {item.id}
            </button>
          ))}
        </div>
      ))}
    </div>
  )

  return (
    <div className="dev-studio__list">
      <MiniDependencyGraph
        nodeId={selectedId}
        relationships={relationships}
        onSelectNode={(id) => void loadNode(id)}
      />
      {renderGroup('Incoming', relationships.incoming)}
      {renderGroup('Outgoing', relationships.outgoing)}
      <div className="dev-studio__graph-section">
        <h3>Connected equations</h3>
        {relationships.connected_equations.map((id) => (
          <button key={id} type="button" className="dev-studio__link" onClick={() => void loadNode(id)}>
            {id}
          </button>
        ))}
      </div>
      <div className="dev-studio__graph-section">
        <h3>Connected workflows</h3>
        {relationships.connected_workflows.map((id) => (
          <button key={id} type="button" className="dev-studio__link" onClick={() => void loadNode(id)}>
            {id}
          </button>
        ))}
      </div>
      <div className="dev-studio__graph-section">
        <h3>Connected sections</h3>
        {relationships.connected_sections.map((id) => (
          <button key={id} type="button" className="dev-studio__link" onClick={() => void loadNode(id)}>
            {id}
          </button>
        ))}
      </div>
    </div>
  )
}
