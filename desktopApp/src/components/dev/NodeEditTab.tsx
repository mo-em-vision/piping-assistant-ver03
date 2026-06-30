import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { CollapsibleSection, Field } from '@/dev-studio/components/fields/FieldComponents'
import {
  devStudioApi,
  type NodeDetail,
  type NodeTypeSchema,
} from '@/dev-studio/api/devStudioApi'
import { useTaskStore } from '@/store/taskStore'

import '@/dev-studio/styles/dev-studio.css'
import './NodeEditTab.css'

interface NodeEditTabProps {
  nodeId: string
  pack: string
  sourceField?: string | null
}

function resolveFocusField(sourceField: string | null | undefined, metadata: Record<string, unknown>): string | null {
  if (!sourceField || sourceField === 'unknown') {
    return null
  }
  if (sourceField in metadata) {
    return sourceField
  }
  if (sourceField === 'display_heading' && 'purpose' in metadata) {
    return 'purpose'
  }
  if (sourceField === 'body') {
    return '__body__'
  }
  return sourceField
}

function sectionForField(schema: NodeTypeSchema | undefined, fieldKey: string): string | null {
  if (!schema?.sections || fieldKey === '__body__') {
    return null
  }
  for (const [section, fields] of Object.entries(schema.sections)) {
    if (fields.includes(fieldKey)) {
      return section
    }
  }
  return null
}

export function NodeEditTab({ nodeId, pack, sourceField }: NodeEditTabProps) {
  const refreshActiveTask = useTaskStore((state) => state.refreshActiveTask)
  const [node, setNode] = useState<NodeDetail | null>(null)
  const [nodeTypes, setNodeTypes] = useState<NodeTypeSchema[]>([])
  const [metadata, setMetadata] = useState<Record<string, unknown>>({})
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})
  const containerRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [detail, types] = await Promise.all([
        devStudioApi.getNode(pack, nodeId),
        devStudioApi.getNodeTypes(),
      ])
      setNode(detail)
      setMetadata({ ...detail.metadata })
      setBody(detail.body)
      setNodeTypes(types.types)
      const focus = resolveFocusField(sourceField, detail.metadata)
      const typeSchema = types.types.find((item) => item.type === detail.type)
      const section = focus ? sectionForField(typeSchema, focus) : null
      const nextOpen: Record<string, boolean> = {}
      if (section) {
        nextOpen[section] = true
      }
      if (focus === '__body__') {
        nextOpen.body = true
      }
      setOpenSections(nextOpen)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load node'
      if (message.includes('404')) {
        setError('Dev Studio API is unavailable. Set DEV_STUDIO_ENABLED=1 on the backend.')
      } else {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }, [nodeId, pack, sourceField])

  useEffect(() => {
    void load()
  }, [load])

  const schema = useMemo(
    () => nodeTypes.find((item) => item.type === node?.type),
    [nodeTypes, node?.type],
  )

  const focusField = useMemo(
    () => resolveFocusField(sourceField, metadata),
    [sourceField, metadata],
  )

  useEffect(() => {
    if (!schema || !focusField) {
      return
    }
    const section = sectionForField(schema, focusField)
    if (section) {
      setOpenSections((current) => ({ ...current, [section]: true }))
    }
    const timer = window.setTimeout(() => {
      const root = containerRef.current
      if (!root) {
        return
      }
      if (focusField === '__body__') {
        root.querySelector<HTMLTextAreaElement>('textarea[data-node-edit-body]')?.focus()
        return
      }
      root.querySelector<HTMLElement>(`[data-node-field="${focusField}"]`)?.focus()
    }, 50)
    return () => window.clearTimeout(timer)
  }, [schema, focusField, loading])

  const updateMeta = (key: string, value: unknown) => {
    setMetadata((prev) => ({ ...prev, [key]: value }))
    setSaveMessage(null)
  }

  const handleSave = async () => {
    if (!node) {
      return
    }
    setSaving(true)
    setError(null)
    setSaveMessage(null)
    try {
      const validation = await devStudioApi.validateNode(pack, {
        metadata,
        body,
        existing_id: node.id,
      })
      if (!validation.valid) {
        const firstError = validation.errors[0]?.message ?? 'Validation failed'
        setError(firstError)
        return
      }
      const updated = await devStudioApi.updateNode(pack, node.id, { metadata, body })
      setNode(updated)
      setMetadata({ ...updated.metadata })
      setBody(updated.body)
      await refreshActiveTask()
      setSaveMessage('Saved. Task view refreshed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const renderScalarField = (key: string) => {
    const value = metadata[key]
    const isLong = key === 'description' || key === 'question' || key.includes('description')
    const isFocused = focusField === key
    if (typeof value === 'boolean') {
      return (
        <Field key={key} label={key}>
          <input
            type="checkbox"
            data-node-field={key}
            checked={value}
            onChange={(event) => updateMeta(key, event.target.checked)}
          />
        </Field>
      )
    }
    if (typeof value === 'object' && value !== null) {
      return (
        <Field key={key} label={key}>
          <textarea
            className={`dev-studio__textarea${isFocused ? ' node-edit-tab__field--focus' : ''}`}
            data-node-field={key}
            value={JSON.stringify(value, null, 2)}
            onChange={(event) => {
              try {
                updateMeta(key, JSON.parse(event.target.value))
              } catch {
                updateMeta(key, event.target.value)
              }
            }}
            rows={4}
          />
        </Field>
      )
    }
    return (
      <Field key={key} label={key}>
        {isLong ? (
          <textarea
            className={`dev-studio__textarea${isFocused ? ' node-edit-tab__field--focus' : ''}`}
            data-node-field={key}
            value={value == null ? '' : String(value)}
            onChange={(event) => updateMeta(key, event.target.value)}
            rows={3}
          />
        ) : (
          <input
            className={`dev-studio__input${isFocused ? ' node-edit-tab__field--focus' : ''}`}
            data-node-field={key}
            value={value == null ? '' : String(value)}
            onChange={(event) => updateMeta(key, event.target.value)}
          />
        )}
      </Field>
    )
  }

  if (loading) {
    return <p className="node-edit-tab__hint">Loading node editor…</p>
  }

  if (error && !node) {
    return <p className="node-edit-tab__error">{error}</p>
  }

  if (!node || !schema) {
    return <p className="node-edit-tab__error">Node editor schema unavailable.</p>
  }

  return (
    <div className="node-edit-tab" ref={containerRef}>
      <header className="node-edit-tab__header">
        <h3 className="node-edit-tab__title">{node.id}</h3>
        <p className="node-edit-tab__meta">
          {node.type}
          {sourceField ? ` · source field: ${sourceField}` : ''}
        </p>
      </header>

      {error ? <p className="node-edit-tab__error">{error}</p> : null}
      {saveMessage ? <p className="node-edit-tab__success">{saveMessage}</p> : null}

      {Object.entries(schema.sections).map(([section, fields]) => (
        <CollapsibleSection
          key={section}
          title={section}
          defaultOpen={openSections[section] ?? (section === 'general' || section === 'ui')}
        >
          {fields.map((field) => (field in metadata ? renderScalarField(field) : null))}
        </CollapsibleSection>
      ))}

      <CollapsibleSection title="Body" defaultOpen={focusField === '__body__' || openSections.body === true}>
        <Field label="Markdown body">
          <textarea
            className={`dev-studio__textarea node-edit-tab__body${focusField === '__body__' ? ' node-edit-tab__field--focus' : ''}`}
            data-node-edit-body
            value={body}
            onChange={(event) => {
              setBody(event.target.value)
              setSaveMessage(null)
            }}
            rows={12}
          />
        </Field>
      </CollapsibleSection>

      <div className="node-edit-tab__actions">
        <button
          type="button"
          className="dev-studio__btn dev-studio__btn--primary"
          disabled={saving}
          onClick={() => void handleSave()}
        >
          {saving ? 'Saving…' : 'Save node'}
        </button>
      </div>
    </div>
  )
}
