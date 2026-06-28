import { backendClient } from '@/services/api/backendClient'

import type { NodeSourceDto, StandardsBrowseDto, TableSourceDto } from '@/types/backend/api'

export const standardsApi = {
  getBrowse(standard = 'asme_b31.3'): Promise<StandardsBrowseDto> {
    const params = new URLSearchParams({ standard })
    return backendClient.request<StandardsBrowseDto>(`/api/v1/standards/browse?${params.toString()}`)
  },

  getNode(nodeId: string): Promise<NodeSourceDto> {
    return backendClient.request<NodeSourceDto>(
      `/api/v1/standards/nodes/${encodeURIComponent(nodeId)}`,
    )
  },

  getNodeSubsection(nodeId: string, subsectionId: string): Promise<NodeSourceDto> {
    return backendClient.request<NodeSourceDto>(
      `/api/v1/standards/nodes/${encodeURIComponent(nodeId)}/subsections/${encodeURIComponent(subsectionId)}`,
    )
  },

  getTable(tableId: string): Promise<TableSourceDto> {
    return backendClient.request<TableSourceDto>(
      `/api/v1/standards/tables/${encodeURIComponent(tableId)}`,
    )
  },
}