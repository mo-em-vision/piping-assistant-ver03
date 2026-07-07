import { useGraphStore } from '../store/graphStore'
import type { ExpansionViewToggles } from '../types'

interface ExpansionToolbarProps {
  onFitView: () => void
  onRefresh: () => void
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <label className="filter-row">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  )
}

export default function ExpansionToolbar({ onFitView, onRefresh }: ExpansionToolbarProps) {
  const toggles = useGraphStore((s) => s.viewToggles)
  const setViewToggle = useGraphStore((s) => s.setViewToggle)

  const setToggle = (key: keyof ExpansionViewToggles) => (value: boolean) => setViewToggle(key, value)

  return (
    <div className="expansion-toolbar">
      <button type="button" className="toolbar-btn" onClick={onFitView}>
        Fit to screen
      </button>
      <button type="button" className="toolbar-btn" onClick={onRefresh}>
        Refresh
      </button>
      <ToggleRow label="Show skipped branches" checked={toggles.showSkipped} onChange={setToggle('showSkipped')} />
      <ToggleRow label="Show full compiled graph" checked={toggles.showFullGraph} onChange={setToggle('showFullGraph')} />
      <ToggleRow label="Show parameter nodes" checked={toggles.showParameters} onChange={setToggle('showParameters')} />
      <ToggleRow label="Show reference edges" checked={toggles.showReferenceEdges} onChange={setToggle('showReferenceEdges')} />
      <ToggleRow label="Auto refresh" checked={toggles.autoRefresh} onChange={setToggle('autoRefresh')} />
    </div>
  )
}
