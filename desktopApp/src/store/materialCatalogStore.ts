import { create } from 'zustand'

import { materialApi } from '@/services/api/materialApi'

const useMockData = import.meta.env.VITE_MOCK_DATA === 'true'

interface MaterialCatalogState {
  ready: boolean
  warming: boolean
  error: string | null
  warmCatalog: () => Promise<void>
  markCatalogReady: () => void
}

export const useMaterialCatalogStore = create<MaterialCatalogState>((set, get) => ({
  ready: useMockData,
  warming: false,
  error: null,

  warmCatalog: async () => {
    if (useMockData || get().ready) {
      set({ ready: true, warming: false, error: null })
      return
    }

    if (get().warming) {
      return
    }

    set({ warming: true, error: null })
    try {
      const response = await materialApi.warm()
      if (response.ready) {
        set({ ready: true, warming: false, error: null })
        return
      }

      set({ ready: false, warming: false, error: null })
    } catch {
      set({ ready: false, warming: false, error: null })
    }
  },

  markCatalogReady: () => {
    set({ ready: true, warming: false, error: null })
  },
}))
