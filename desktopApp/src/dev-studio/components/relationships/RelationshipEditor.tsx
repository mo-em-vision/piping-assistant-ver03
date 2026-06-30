import type { NodeTypeSchema } from '@/dev-studio/api/devStudioApi'
import { CollapsibleSection, NodeMultiSelect } from '@/dev-studio/components/fields/FieldComponents'

const GRAPH_FIELDS = new Set([
  'requires',
  'calculates',
  'defines',
  'explains',
  'outputs',
  'contains',
  'anchors_to',
  'uses_table',
  'next_step',
  'validates',
  'located_in',
  'defined_by',
  'related_to',
  'references',
  'uses',
  'accepts',
  'depends_on',
  'edges',
  'goal_output',
])

interface RelationshipEditorProps {
  metadata: Record<string, unknown>
  schema: NodeTypeSchema | undefined
  allNodeIds: string[]
  onChange: (key: string, value: unknown) => void
}

export function RelationshipEditor({
  metadata,
  schema,
  allNodeIds,
  onChange,
}: RelationshipEditorProps) {
  const graphFields = new Set<string>(schema?.graph_fields ?? [])
  const graphSection = schema?.sections?.graph
  if (graphSection) {
    for (const field of graphSection) graphFields.add(field)
  }

  const fieldsToShow = [...graphFields].filter((key) => key in metadata || GRAPH_FIELDS.has(key))

  const ensureField = (key: string): string[] => {
    const value = metadata[key]
    if (Array.isArray(value)) {
      return value.map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'node_id' in item) return String(item.node_id)
        if (item && typeof item === 'object' && 'to' in item) return String(item.to)
        return String(item)
      })
    }
    if (typeof value === 'string' && value) return [value]
    return []
  }

  if (!fieldsToShow.length) {
    return null
  }

  return (
    <CollapsibleSection title="Relationships">
      {fieldsToShow.map((key) => {
        const raw = metadata[key]
        if (key === 'edges' && Array.isArray(raw)) {
          return (
            <div key={key} className="dev-studio__field">
              <label>{key} (edit as JSON in Additional fields)</label>
              <div className="dev-studio__list-item-meta">{raw.length} edge(s)</div>
            </div>
          )
        }
        if (typeof raw === 'string') {
          return (
            <NodeMultiSelect
              key={key}
              label={key}
              selected={raw ? [raw] : []}
              options={allNodeIds}
              onChange={(vals) => onChange(key, vals[0] ?? '')}
            />
          )
        }
        return (
          <NodeMultiSelect
            key={key}
            label={key}
            selected={ensureField(key)}
            options={allNodeIds}
            onChange={(vals) => onChange(key, vals)}
          />
        )
      })}
    </CollapsibleSection>
  )
}
