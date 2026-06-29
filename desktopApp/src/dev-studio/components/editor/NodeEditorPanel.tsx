import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  CollapsibleSection,
  Field,
  NodeMultiSelect,
  TagEditor,
  ValidationBanner,
} from '@/dev-studio/components/fields/FieldComponents'
import { EquationEditor } from '@/dev-studio/components/equation/EquationEditor'
import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

const SECTION_LABELS: Record<string, string> = {
  general: 'General',
  calculation: 'Calculation',
  engineering: 'Engineering',
  graph: 'Graph',
  ui: 'UI',
  metadata: 'Metadata',
}

function stringifyField(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function parseFieldValue(raw: string, original: unknown): unknown {
  if (typeof original === 'number') {
    const n = Number(raw)
    return Number.isNaN(n) ? raw : n
  }
  if (typeof original === 'boolean') return raw === 'true'
  if (typeof original === 'object' && original !== null) {
    try {
      return JSON.parse(raw)
    } catch {
      return raw
    }
  }
  return raw
}

export function NodeEditorPanel() {
  const selectedNode = useDevStudioStore((s) => s.selectedNode)
  const nodeTypes = useDevStudioStore((s) => s.nodeTypes)
  const nodes = useDevStudioStore((s) => s.nodes)
  const pack = useDevStudioStore((s) => s.pack)
  const validation = useDevStudioStore((s) => s.validation)
  const saving = useDevStudioStore((s) => s.saving)
  const saveError = useDevStudioStore((s) => s.saveError)
  const dirty = useDevStudioStore((s) => s.dirty)
  const saveNode = useDevStudioStore((s) => s.saveNode)
  const setDirty = useDevStudioStore((s) => s.setDirty)
  const deleteSelectedNode = useDevStudioStore((s) => s.deleteSelectedNode)
  const duplicateNode = useDevStudioStore((s) => s.duplicateNode)
  const createNode = useDevStudioStore((s) => s.createNode)

  const [metadata, setMetadata] = useState<Record<string, unknown>>({})
  const [body, setBody] = useState('')

  useEffect(() => {
    if (selectedNode) {
      setMetadata({ ...selectedNode.metadata })
      setBody(selectedNode.body)
      setDirty(false)
    }
  }, [selectedNode, setDirty])

  const schema = useMemo(
    () => nodeTypes.find((t) => t.type === selectedNode?.type),
    [nodeTypes, selectedNode?.type],
  )

  const allNodeIds = useMemo(() => nodes.map((n) => n.id), [nodes])

  const schemaFields = useMemo(() => {
    const fields = new Set<string>()
    if (schema?.sections) {
      Object.values(schema.sections).forEach((list) => list.forEach((f) => fields.add(f)))
    }
    return fields
  }, [schema])

  const additionalFields = useMemo(
    () => Object.keys(metadata).filter((k) => !schemaFields.has(k) && k !== 'id' && k !== 'type'),
    [metadata, schemaFields],
  )

  const updateMeta = useCallback(
    (key: string, value: unknown) => {
      setMetadata((prev) => ({ ...prev, [key]: value }))
      setDirty(true)
    },
    [setDirty],
  )

  const handleSave = useCallback(async () => {
    await saveNode(metadata, body)
  }, [saveNode, metadata, body])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        void handleSave()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [handleSave])

  useEffect(() => {
    if (!dirty) return
    const timer = window.setTimeout(() => void handleSave(), 500)
    return () => window.clearTimeout(timer)
  }, [metadata, body, dirty, handleSave])

  const renderField = (key: string) => {
    const value = metadata[key]
    if (key === 'tags' && Array.isArray(value)) {
      return (
        <Field key={key} label={key}>
          <TagEditor value={value.map(String)} onChange={(tags) => updateMeta(key, tags)} />
        </Field>
      )
    }
    if (
      Array.isArray(value) &&
      (value.every((v) => typeof v === 'string') || schema?.graph_fields.includes(key))
    ) {
      const selected = value.map(String)
      return (
        <NodeMultiSelect
          key={key}
          label={key}
          selected={selected}
          options={allNodeIds}
          onChange={(vals) => updateMeta(key, vals)}
        />
      )
    }
    if (typeof value === 'boolean') {
      return (
        <Field key={key} label={key}>
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => updateMeta(key, e.target.checked)}
          />
        </Field>
      )
    }
    if (typeof value === 'object' && value !== null) {
      return (
        <Field key={key} label={key}>
          <textarea
            className="dev-studio__textarea"
            value={stringifyField(value)}
            onChange={(e) => updateMeta(key, parseFieldValue(e.target.value, value))}
            rows={4}
          />
        </Field>
      )
    }
    const isLong = key === 'description' || key === 'question' || key.includes('description')
    return (
      <Field key={key} label={key}>
        {isLong ? (
          <textarea
            className="dev-studio__textarea"
            value={stringifyField(value)}
            onChange={(e) => updateMeta(key, e.target.value)}
            rows={3}
          />
        ) : (
          <input
            className="dev-studio__input"
            value={stringifyField(value)}
            onChange={(e) => updateMeta(key, parseFieldValue(e.target.value, value))}
          />
        )}
      </Field>
    )
  }

  if (!selectedNode) {
    return (
      <div className="dev-studio__editor">
        <div className="dev-studio__empty">
          Select a node from the list, or{' '}
          <button
            type="button"
            className="dev-studio__link"
            onClick={() =>
              void createNode({
                id: `NEW-node-${Date.now()}`,
                type: 'parameter',
                symbol: 'x',
                input_id: 'x',
                title: 'New parameter',
                description: 'New node',
              })
            }
          >
            create a new node
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="dev-studio__editor">
      {validation && (
        <ValidationBanner errors={validation.errors} warnings={validation.warnings} />
      )}
      {saveError && (
        <div className="dev-studio__validation dev-studio__validation--error">{saveError}</div>
      )}

      <CollapsibleSection title="General">
        <Field label="id">
          <input
            className="dev-studio__input"
            value={String(metadata.id ?? '')}
            onChange={(e) => updateMeta('id', e.target.value)}
          />
        </Field>
        <Field label="type">
          <select
            className="dev-studio__select"
            value={String(metadata.type ?? '')}
            onChange={(e) => updateMeta('type', e.target.value)}
          >
            {nodeTypes.map((t) => (
              <option key={t.type} value={t.type}>
                {t.type}
              </option>
            ))}
          </select>
        </Field>
      </CollapsibleSection>

      {schema?.sections &&
        Object.entries(schema.sections).map(([sectionKey, fields]) => (
          <CollapsibleSection key={sectionKey} title={SECTION_LABELS[sectionKey] ?? sectionKey}>
            {fields.filter((f) => f !== 'id' && f !== 'type').map((f) => renderField(f))}
          </CollapsibleSection>
        ))}

      {selectedNode.type === 'equation' && (
        <EquationEditor
          pack={pack}
          nodeId={selectedNode.id}
          sympy={String(metadata.sympy ?? '')}
          displayLatex={String(metadata.display_latex ?? '')}
          onSympyChange={(v) => updateMeta('sympy', v)}
          onDisplayChange={(v) => updateMeta('display_latex', v)}
        />
      )}

      {additionalFields.length > 0 && (
        <CollapsibleSection title="Additional fields" defaultOpen={false}>
          {additionalFields.map((key) => renderField(key))}
        </CollapsibleSection>
      )}

      <CollapsibleSection title="Body (Markdown)">
        <textarea
          className="dev-studio__textarea"
          value={body}
          onChange={(e) => {
            setBody(e.target.value)
            setDirty(true)
          }}
          rows={8}
        />
      </CollapsibleSection>

      <div className="dev-studio__toolbar">
        <button type="button" className="dev-studio__btn dev-studio__btn--primary" onClick={() => void handleSave()}>
          {saving ? 'Saving…' : dirty ? 'Save changes' : 'Saved'}
        </button>
        <button
          type="button"
          className="dev-studio__btn"
          onClick={() => {
            const newId = window.prompt('New node ID for duplicate:', `${selectedNode.id}-copy`)
            if (newId) void duplicateNode(newId)
          }}
        >
          Duplicate
        </button>
        <button
          type="button"
          className="dev-studio__btn dev-studio__btn--danger"
          onClick={() => {
            if (window.confirm(`Delete ${selectedNode.id}?`)) void deleteSelectedNode()
          }}
        >
          Delete
        </button>
      </div>
    </div>
  )
}
