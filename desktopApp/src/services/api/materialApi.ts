import { backendClient } from '@/services/api/backendClient'

import type { MaterialSearchResponse } from '@/types/backend/materials'

export interface MaterialWarmResponse {
  ready: boolean
  cached?: boolean
  reason?: string
}

export const materialApi = {
  warm(): Promise<MaterialWarmResponse> {
    return backendClient.request<MaterialWarmResponse>('/api/v1/materials/warm')
  },

  search(query: string): Promise<MaterialSearchResponse> {
    const params = new URLSearchParams({ q: query })
    return backendClient.request<MaterialSearchResponse>(`/api/v1/materials/search?${params.toString()}`)
  },
}
