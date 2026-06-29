import { backendClient } from '@/services/api/backendClient'

export interface NodeSummary {
  id: string
  type: string
  title: string
  description: string
  source_rel_path: string
  unit: string
  category: string
  tags: string[]
}

export interface NodeDetail {
  pack: string
  id: string
  type: string
  metadata: Record<string, unknown>
  body: string
  source_rel_path: string
  incoming: Array<{ from_id: string; to_id: string; type: string; metadata: Record<string, unknown> }>
  outgoing: Array<{ from_id: string; to_id: string; type: string; metadata: Record<string, unknown> }>
}

export interface NodeTypeSchema {
  type: string
  required: string[]
  sections: Record<string, string[]>
  graph_fields: string[]
}

export interface ValidationResult {
  valid: boolean
  errors: Array<{ field: string; message: string; severity: string }>
  warnings: Array<{ field: string; message: string; severity: string }>
}

export interface RelationshipsPayload {
  node_id: string
  incoming: Record<string, Array<{ id: string; type: string }>>
  outgoing: Record<string, Array<{ id: string; type: string }>>
  connected_equations: string[]
  connected_workflows: string[]
  connected_sections: string[]
}

function packQuery(pack: string) {
  return `pack=${encodeURIComponent(pack)}`
}

export const devStudioApi = {
  listPacks() {
    return backendClient.get<{ packs: Array<{ slug: string; node_count: number; revision: string }> }>(
      '/api/v1/dev/packs',
    )
  },

  getNodeTypes() {
    return backendClient.get<{ types: NodeTypeSchema[] }>('/api/v1/dev/node-types')
  },

  listNodes(pack: string, type?: string) {
    const typeQuery = type ? `&type=${encodeURIComponent(type)}` : ''
    return backendClient.get<{ nodes: NodeSummary[]; count: number }>(
      `/api/v1/dev/nodes?${packQuery(pack)}${typeQuery}`,
    )
  },

  searchNodes(pack: string, q: string, type?: string) {
    const typeQuery = type ? `&type=${encodeURIComponent(type)}` : ''
    return backendClient.get<{ nodes: NodeSummary[]; count: number }>(
      `/api/v1/dev/search?${packQuery(pack)}&q=${encodeURIComponent(q)}${typeQuery}`,
    )
  },

  getNode(pack: string, id: string) {
    return backendClient.get<NodeDetail>(`/api/v1/dev/nodes/${encodeURIComponent(id)}?${packQuery(pack)}`)
  },

  createNode(pack: string, payload: { metadata: Record<string, unknown>; body?: string; source_rel_path?: string }) {
    return backendClient.post<NodeDetail>(`/api/v1/dev/nodes?${packQuery(pack)}`, payload)
  },

  updateNode(
    pack: string,
    id: string,
    payload: { metadata: Record<string, unknown>; body?: string; source_rel_path?: string; force?: boolean },
  ) {
    return backendClient.put<NodeDetail>(
      `/api/v1/dev/nodes/${encodeURIComponent(id)}?${packQuery(pack)}`,
      payload,
    )
  },

  deleteNode(pack: string, id: string) {
    return backendClient.delete<{ deleted: boolean; id: string }>(
      `/api/v1/dev/nodes/${encodeURIComponent(id)}?${packQuery(pack)}`,
    )
  },

  duplicateNode(pack: string, id: string, newId: string, sourceRelPath?: string) {
    return backendClient.post<NodeDetail>(
      `/api/v1/dev/nodes/${encodeURIComponent(id)}/duplicate?${packQuery(pack)}`,
      { new_id: newId, source_rel_path: sourceRelPath },
    )
  },

  validateNode(
    pack: string,
    payload: { metadata: Record<string, unknown>; body?: string; existing_id?: string },
  ) {
    return backendClient.post<ValidationResult>(`/api/v1/dev/nodes/validate?${packQuery(pack)}`, payload)
  },

  getRelationships(pack: string, nodeId: string) {
    return backendClient.get<RelationshipsPayload>(
      `/api/v1/dev/relationships?${packQuery(pack)}&node_id=${encodeURIComponent(nodeId)}`,
    )
  },

  getRevision(pack: string) {
    return backendClient.get<{ revision: string; node_count: number; updated_at: string }>(
      `/api/v1/dev/revision?${packQuery(pack)}`,
    )
  },

  previewEquation(
    pack: string,
    nodeId: string,
    payload: { sympy?: string; display_latex?: string; symbol_values: Record<string, number> },
  ) {
    return backendClient.post<{ valid: boolean; outputs?: Record<string, number>; error?: string; display?: string }>(
      `/api/v1/dev/nodes/${encodeURIComponent(nodeId)}/equation/preview?${packQuery(pack)}`,
      payload,
    )
  },

  bulkAction(
    pack: string,
    payload: { action: string; node_ids: string[]; tags?: string[]; topic?: string },
  ) {
    return backendClient.post<{ action: string; deleted?: string[]; updated?: string[] }>(
      `/api/v1/dev/nodes/bulk?${packQuery(pack)}`,
      payload,
    )
  },

  exportNodes(pack: string, fmt: 'json' | 'markdown' | 'csv', ids?: string[]) {
    const idsQuery = ids?.length ? `&ids=${encodeURIComponent(ids.join(','))}` : ''
    return backendClient.get<{ format: string; content?: unknown; files?: Array<{ path: string; content: string }> }>(
      `/api/v1/dev/export?${packQuery(pack)}&format=${fmt}${idsQuery}`,
    )
  },

  importNodes(pack: string, payload: { format: string; nodes: unknown[] }) {
    return backendClient.post<{ created: string[]; updated: string[]; errors: Array<{ id: string; message: string }> }>(
      `/api/v1/dev/import?${packQuery(pack)}`,
      payload,
    )
  },
}
