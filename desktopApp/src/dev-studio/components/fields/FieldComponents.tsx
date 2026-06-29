import { useMemo, useState } from 'react'

interface CollapsibleSectionProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

export function CollapsibleSection({ title, children, defaultOpen = true }: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="dev-studio__card">
      <div className="dev-studio__card-header" onClick={() => setOpen((v) => !v)}>
        <span>{title}</span>
        <span>{open ? '▾' : '▸'}</span>
      </div>
      {open && <div className="dev-studio__card-body">{children}</div>}
    </div>
  )
}

interface FieldProps {
  label: string
  children: React.ReactNode
}

export function Field({ label, children }: FieldProps) {
  return (
    <div className="dev-studio__field">
      <label>{label}</label>
      {children}
    </div>
  )
}

interface TagEditorProps {
  value: string[]
  onChange: (tags: string[]) => void
}

export function TagEditor({ value, onChange }: TagEditorProps) {
  const [draft, setDraft] = useState('')
  const addTag = () => {
    const tag = draft.trim()
    if (!tag || value.includes(tag)) return
    onChange([...value, tag])
    setDraft('')
  }
  return (
    <div>
      <div className="dev-studio__tag-list">
        {value.map((tag) => (
          <span key={tag} className="dev-studio__tag">
            {tag}{' '}
            <button type="button" className="dev-studio__link" onClick={() => onChange(value.filter((t) => t !== tag))}>
              ×
            </button>
          </span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        <input
          className="dev-studio__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
          placeholder="Add tag"
        />
        <button type="button" className="dev-studio__btn" onClick={addTag}>
          Add
        </button>
      </div>
    </div>
  )
}

interface NodeMultiSelectProps {
  label: string
  selected: string[]
  options: string[]
  onChange: (values: string[]) => void
}

export function NodeMultiSelect({ label, selected, options, onChange }: NodeMultiSelectProps) {
  const [filter, setFilter] = useState('')
  const filtered = useMemo(
    () => options.filter((id) => id.toLowerCase().includes(filter.toLowerCase())),
    [filter, options],
  )
  return (
    <Field label={label}>
      <input
        className="dev-studio__input"
        placeholder="Search nodes..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div className="dev-studio__multi-select">
        {filtered.slice(0, 100).map((id) => (
          <label key={id}>
            <input
              type="checkbox"
              checked={selected.includes(id)}
              onChange={(e) => {
                if (e.target.checked) onChange([...selected, id])
                else onChange(selected.filter((v) => v !== id))
              }}
            />
            {id}
          </label>
        ))}
      </div>
    </Field>
  )
}

export function ValidationBanner({
  errors,
  warnings,
}: {
  errors: Array<{ field: string; message: string }>
  warnings: Array<{ field: string; message: string }>
}) {
  if (!errors.length && !warnings.length) return null
  return (
    <>
      {errors.length > 0 && (
        <div className="dev-studio__validation dev-studio__validation--error">
          {errors.map((e) => (
            <div key={`${e.field}-${e.message}`}>
              <strong>{e.field}:</strong> {e.message}
            </div>
          ))}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="dev-studio__validation dev-studio__validation--warning">
          {warnings.map((w) => (
            <div key={`${w.field}-${w.message}`}>
              <strong>{w.field}:</strong> {w.message}
            </div>
          ))}
        </div>
      )}
    </>
  )
}
