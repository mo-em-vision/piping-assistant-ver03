import { create } from 'zustand'

import { backendClient } from '@/services/api/backendClient'
import { buildHealthUrl } from '@/config/constants'

type ApiConnectionStatus = 'idle' | 'checking' | 'connected' | 'error'

interface ConnectionState {
  apiStatus: ApiConnectionStatus
  apiError: string | null
  lastCheckedAt: string | null
  checkApiConnection: () => Promise<boolean>
  reset: () => void
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  apiStatus: 'idle',
  apiError: null,
  lastCheckedAt: null,
  checkApiConnection: async () => {
    set({ apiStatus: 'checking', apiError: null })
    try {
      const response = await fetch(buildHealthUrl(backendClient.getBaseUrl()), {
        signal: AbortSignal.timeout(3_000),
      })
      if (!response.ok) {
        throw new Error(`Health check failed (${response.status})`)
      }
      set({
        apiStatus: 'connected',
        apiError: null,
        lastCheckedAt: new Date().toISOString(),
      })
      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : 'API unavailable'
      set({
        apiStatus: 'error',
        apiError: message,
        lastCheckedAt: new Date().toISOString(),
      })
      return false
    }
  },
  reset: () => set({ apiStatus: 'idle', apiError: null, lastCheckedAt: null }),
}))
