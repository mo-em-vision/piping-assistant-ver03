import { useEffect, useRef } from 'react'

import { BulkActionBar } from '@/dev-studio/components/bulk/BulkActionBar'
import { NodeEditorPanel } from '@/dev-studio/components/editor/NodeEditorPanel'
import { GraphPanel } from '@/dev-studio/components/graph/GraphPanel'
import { NodeListPanel } from '@/dev-studio/components/sidebar/NodeListPanel'
import { useDebouncedValue } from '@/dev-studio/hooks/useDebouncedSearch'
import { useRevisionPoll } from '@/dev-studio/hooks/useRevisionPoll'
import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

export function DevStudioApp() {
  const searchRef = useRef<HTMLInputElement>(null)
  const pack = useDevStudioStore((s) => s.pack)
  const packs = useDevStudioStore((s) => s.packs)
  const nodes = useDevStudioStore((s) => s.nodes)
  const typeFilter = useDevStudioStore((s) => s.typeFilter)
  const searchQuery = useDevStudioStore((s) => s.searchQuery)
  const nodeTypes = useDevStudioStore((s) => s.nodeTypes)
  const dirty = useDevStudioStore((s) => s.dirty)
  const loading = useDevStudioStore((s) => s.loading)
  const bootstrap = useDevStudioStore((s) => s.bootstrap)
  const refreshNodes = useDevStudioStore((s) => s.refreshNodes)
  const setPack = useDevStudioStore((s) => s.setPack)
  const setTypeFilter = useDevStudioStore((s) => s.setTypeFilter)
  const setSearchQuery = useDevStudioStore((s) => s.setSearchQuery)
  const createNode = useDevStudioStore((s) => s.createNode)
  const selectedId = useDevStudioStore((s) => s.selectedId)
  const loadNode = useDevStudioStore((s) => s.loadNode)
  const duplicateNode = useDevStudioStore((s) => s.duplicateNode)
  const deleteSelectedNode = useDevStudioStore((s) => s.deleteSelectedNode)

  const debouncedSearch = useDebouncedValue(searchQuery, 250)

  useRevisionPoll()

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  useEffect(() => {
    void refreshNodes()
  }, [pack, typeFilter, debouncedSearch, refreshNodes])

  useEffect(() => {
    const isEditable = (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement)) return false
      const tag = target.tagName
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable
    }

    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault()
        searchRef.current?.focus()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        void createNode({
          id: `NEW-node-${Date.now()}`,
          type: 'parameter',
          symbol: 'x',
          input_id: 'x',
          title: 'New parameter',
          description: 'New node',
        })
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'd' && selectedId) {
        e.preventDefault()
        const newId = window.prompt('New node ID for duplicate:', `${selectedId}-copy`)
        if (newId) void duplicateNode(newId)
      }
      if (e.key === 'Delete' && selectedId && !isEditable(e.target)) {
        e.preventDefault()
        if (window.confirm(`Delete ${selectedId}?`)) void deleteSelectedNode()
      }
      if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && !isEditable(e.target) && nodes.length) {
        e.preventDefault()
        const idx = nodes.findIndex((n) => n.id === selectedId)
        const start = idx < 0 ? 0 : idx
        const next = e.key === 'ArrowDown' ? Math.min(start + 1, nodes.length - 1) : Math.max(start - 1, 0)
        if (nodes[next]) void loadNode(nodes[next].id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [createNode, selectedId, duplicateNode, deleteSelectedNode, loadNode, nodes])

  return (
    <div className="dev-studio">
      <header className="dev-studio__header">
        <h1>Node Dev Studio</h1>
        <span className="dev-studio__badge">Development only</span>
        <select
          className="dev-studio__select"
          style={{ width: 180 }}
          value={pack}
          onChange={(e) => setPack(e.target.value)}
        >
          {packs.map((p) => (
            <option key={p.slug} value={p.slug}>
              {p.slug} ({p.node_count})
            </option>
          ))}
        </select>
        <span className={`dev-studio__status${dirty ? ' dev-studio__status--dirty' : ''}`}>
          {loading ? 'Loading…' : dirty ? 'Unsaved changes' : 'Up to date'}
        </span>
      </header>

      <BulkActionBar />

      <div className="dev-studio__panels">
        <aside className="dev-studio__panel">
          <div className="dev-studio__panel-header">
            <input
              ref={searchRef}
              className="dev-studio__input"
              placeholder="Search nodes (Ctrl+F)…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <select
              className="dev-studio__select"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="">All types</option>
              {nodeTypes.map((t) => (
                <option key={t.type} value={t.type}>
                  {t.type}
                </option>
              ))}
            </select>
          </div>
          <NodeListPanel nodes={nodes} />
        </aside>

        <main className="dev-studio__panel">
          <NodeEditorPanel />
        </main>

        <aside className="dev-studio__panel dev-studio__panel--right">
          <div className="dev-studio__panel-header">
            <strong>Graph context</strong>
          </div>
          <GraphPanel />
        </aside>
      </div>
    </div>
  )
}
