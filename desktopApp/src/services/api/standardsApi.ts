import { backendClient } from '@/services/api/backendClient'

import type { NodeSourceDto, TableSourceDto } from '@/types/backend/api'

export const standardsApi = {
  getNode(nodeId: string): Promise<NodeSourceDto> {
    return backendClient.request<NodeSourceDto>(
      `/api/v1/standards/nodes/${encodeURIComponent(nodeId)}`,
    )
  },

  getTable(tableId: string): Promise<TableSourceDto> {
    return backendClient.request<TableSourceDto>(
      `/api/v1/standards/tables/${encodeURIComponent(tableId)}`,
    )
  },
}