import { create } from 'zustand'

import {
  devStudioApi,
  type NodeDetail,
  type NodeSummary,
  type NodeTypeSchema,
  type RelationshipsPayload,
  type ValidationResult,
} from '@/dev-studio/api/devStudioApi'

interface DevStudioState {
  pack: string
  packs: Array<{ slug: string; node_count: number; revision: string }>
  nodes: NodeSummary[]
  nodeCount: number
  typeFilter: string
  searchQuery: string
  selectedId: string | null
  selectedNode: NodeDetail | null
  relationships: RelationshipsPayload | null
  nodeTypes: NodeTypeSchema[]
  selectedIds: Set<string>
  revision: string | null
  loading: boolean
  saving: boolean
  validation: ValidationResult | null
  saveError: string | null
  dirty: boolean

  setPack: (pack: string) => void
  setTypeFilter: (type: string) => void
  setSearchQuery: (q: string) => void
  setSelectedId: (id: string | null) => void
  toggleSelected: (id: string) => void
  clearSelection: () => void
  setDirty: (dirty: boolean) => void
  bootstrap: () => Promise<void>
  refreshNodes: () => Promise<void>
  loadNode: (id: string) => Promise<void>
  saveNode: (metadata: Record<string, unknown>, body: string) => Promise<boolean>
  deleteSelectedNode: () => Promise<void>
  duplicateNode: (newId: string) => Promise<void>
  createNode: (metadata: Record<string, unknown>, body?: string) => Promise<void>
  checkRevision: () => Promise<void>
  bulkDelete: () => Promise<void>
  bulkAddTags: (tags: string[]) => Promise<void>
  exportSelected: (fmt: 'json' | 'markdown' | 'csv') => Promise<void>
}

export const useDevStudioStore = create<DevStudioState>((set, get) => ({
  pack: 'asme_b31.3',
  packs: [],
  nodes: [],
  nodeCount: 0,
  typeFilter: '',
  searchQuery: '',
  selectedId: null,
  selectedNode: null,
  relationships: null,
  nodeTypes: [],
  selectedIds: new Set(),
  revision: null,
  loading: false,
  saving: false,
  validation: null,
  saveError: null,
  dirty: false,

  setPack: (pack) => set({ pack, selectedId: null, selectedNode: null, relationships: null }),
  setTypeFilter: (typeFilter) => set({ typeFilter }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSelectedId: (selectedId) => set({ selectedId }),
  toggleSelected: (id) => {
    const next = new Set(get().selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    set({ selectedIds: next })
  },
  clearSelection: () => set({ selectedIds: new Set() }),
  setDirty: (dirty) => set({ dirty }),

  bootstrap: async () => {
    set({ loading: true })
    try {
      const [packsRes, typesRes] = await Promise.all([
        devStudioApi.listPacks(),
        devStudioApi.getNodeTypes(),
      ])
      const packs = packsRes.packs
      const defaultPack = packs.find((p) => p.slug === 'asme_b31.3')?.slug ?? packs[0]?.slug ?? 'asme_b31.3'
      set({ packs, nodeTypes: typesRes.types, pack: defaultPack })
      await get().refreshNodes()
    } finally {
      set({ loading: false })
    }
  },

  refreshNodes: async () => {
    const { pack, searchQuery, typeFilter } = get()
    const type = typeFilter || undefined
    const res = searchQuery.trim()
      ? await devStudioApi.searchNodes(pack, searchQuery.trim(), type)
      : await devStudioApi.listNodes(pack, type)
    const rev = await devStudioApi.getRevision(pack)
    set({ nodes: res.nodes, nodeCount: res.count, revision: rev.revision })
  },

  loadNode: async (id) => {
    const { pack } = get()
    set({ loading: true, saveError: null, validation: null })
    try {
      const [node, rels] = await Promise.all([
        devStudioApi.getNode(pack, id),
        devStudioApi.getRelationships(pack, id),
      ])
      set({ selectedId: id, selectedNode: node, relationships: rels, dirty: false })
    } finally {
      set({ loading: false })
    }
  },

  saveNode: async (metadata, body) => {
    const { pack, selectedId, selectedNode } = get()
    if (!selectedId || !selectedNode) return false
    set({ saving: true, saveError: null })
    try {
      const validation = await devStudioApi.validateNode(pack, {
        metadata,
        body,
        existing_id: selectedId,
      })
      set({ validation })
      if (!validation.valid) {
        set({ saveError: 'Validation failed' })
        return false
      }
      const updated = await devStudioApi.updateNode(pack, selectedId, { metadata, body })
      set({ selectedNode: updated, selectedId: updated.id, dirty: false })
      await get().refreshNodes()
      if (updated.id !== selectedId) {
        await get().loadNode(updated.id)
      } else {
        const rels = await devStudioApi.getRelationships(pack, updated.id)
        set({ relationships: rels })
      }
      return true
    } catch (err) {
      set({ saveError: err instanceof Error ? err.message : 'Save failed' })
      return false
    } finally {
      set({ saving: false })
    }
  },

  deleteSelectedNode: async () => {
    const { pack, selectedId } = get()
    if (!selectedId) return
    await devStudioApi.deleteNode(pack, selectedId)
    set({ selectedId: null, selectedNode: null, relationships: null })
    await get().refreshNodes()
  },

  duplicateNode: async (newId) => {
    const { pack, selectedId } = get()
    if (!selectedId) return
    const dup = await devStudioApi.duplicateNode(pack, selectedId, newId)
    await get().refreshNodes()
    await get().loadNode(dup.id)
  },

  createNode: async (metadata, body = '') => {
    const { pack } = get()
    const created = await devStudioApi.createNode(pack, { metadata, body })
    await get().refreshNodes()
    await get().loadNode(created.id)
  },

  checkRevision: async () => {
    const { pack, revision, selectedId, dirty } = get()
    const rev = await devStudioApi.getRevision(pack)
    if (rev.revision !== revision) {
      await get().refreshNodes()
      if (selectedId && !dirty) {
        await get().loadNode(selectedId)
      }
    }
  },

  bulkDelete: async () => {
    const { pack, selectedIds } = get()
    const ids = [...selectedIds]
    if (!ids.length) return
    await devStudioApi.bulkAction(pack, { action: 'delete', node_ids: ids })
    set({ selectedIds: new Set(), selectedId: null, selectedNode: null })
    await get().refreshNodes()
  },

  bulkAddTags: async (tags) => {
    const { pack, selectedIds } = get()
    const ids = [...selectedIds]
    if (!ids.length) return
    await devStudioApi.bulkAction(pack, { action: 'add_tags', node_ids: ids, tags })
    await get().refreshNodes()
    const { selectedId } = get()
    if (selectedId) await get().loadNode(selectedId)
  },

  exportSelected: async (fmt) => {
    const { pack, selectedIds, nodes } = get()
    const ids = selectedIds.size ? [...selectedIds] : nodes.map((n) => n.id)
    const res = await devStudioApi.exportNodes(pack, fmt, ids)
    let content = ''
    let filename = `nodes-export.${fmt}`
    if (fmt === 'json') {
      content = JSON.stringify(res.content, null, 2)
    } else if (fmt === 'csv') {
      content = String(res.content ?? '')
    } else if (fmt === 'markdown' && res.files) {
      content = res.files.map((f) => `# ${f.path}\n${f.content}`).join('\n\n---\n\n')
      filename = 'nodes-export.md'
    }
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}))
