import { useGraphStore } from '../store/graphStore'
import { ALL_NODE_TYPES, nodeStyle } from '../utils/nodeStyles'

export default function FilterBar() {
  const visibleTypes = useGraphStore((s) => s.visibleTypes)
  const toggleType = useGraphStore((s) => s.toggleType)

  return (
    <div>
      <div className="section-title">Node types</div>
      {ALL_NODE_TYPES.map((nodeType) => {
        const style = nodeStyle(nodeType)
        return (
          <label key={nodeType} className="filter-row">
            <input
              type="checkbox"
              checked={visibleTypes.has(nodeType)}
              onChange={() => toggleType(nodeType)}
            />
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                background: style.border,
                display: 'inline-block',
              }}
            />
            {style.label}
          </label>
        )
      })}
    </div>
  )
}
