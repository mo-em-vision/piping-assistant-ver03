import { backendClient } from '@/services/api/backendClient'

import type { MaterialSearchResponse } from '@/types/backend/materials'

export const materialApi = {
  search(query: string): Promise<MaterialSearchResponse> {
    const params = new URLSearchParams({ q: query })
    return backendClient.request<MaterialSearchResponse>(`/api/v1/materials/search?${params.toString()}`)
  },
}
