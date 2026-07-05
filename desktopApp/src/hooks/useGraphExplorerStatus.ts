import { useCallback, useEffect, useState } from 'react'

import type { GraphExplorerStatusPayload } from '@/config/constants'
import { constants } from '@/config/constants'

const defaultStatus: GraphExplorerStatusPayload = {
  status: 'stopped',
  url: constants.graphExplorerUrl,
}

export function useGraphExplorerStatus(): {
  status: GraphExplorerStatusPayload
  refresh: () => Promise<void>
} {
  const [status, setStatus] = useState<GraphExplorerStatusPayload>(defaultStatus)

  const refresh = useCallback(async () => {
    const payload = await window.electronAPI?.getGraphExplorerStatus?.()
    if (payload) {
      setStatus(payload)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const unsubscribe = window.electronAPI?.onGraphExplorerStatusChange?.((payload) => {
      setStatus(payload)
    })
    return unsubscribe
  }, [refresh])

  return { status, refresh }
}
