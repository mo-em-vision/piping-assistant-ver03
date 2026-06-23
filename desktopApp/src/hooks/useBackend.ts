import { useCallback, useEffect, useState } from 'react'

import type { BackendStatusPayload } from '@/config/constants'

const defaultStatus: BackendStatusPayload = {
  status: 'starting',
  url: 'http://localhost:8000',
}

export function useBackendConnection() {
  const [backendStatus, setBackendStatus] = useState<BackendStatusPayload>(defaultStatus)
  const [isRetrying, setIsRetrying] = useState(false)

  useEffect(() => {
    const api = window.electronAPI
    if (!api) {
      return
    }

    void api.getBackendStatus().then((status) => {
      if (status) {
        setBackendStatus(status)
      }
    })

    return api.onBackendStatusChange(setBackendStatus)
  }, [])

  const retryConnection = useCallback(async () => {
    const api = window.electronAPI
    if (!api || isRetrying) {
      return
    }

    setIsRetrying(true)
    try {
      const status = await api.retryBackendConnection()
      if (status) {
        setBackendStatus(status)
      }
    } finally {
      setIsRetrying(false)
    }
  }, [isRetrying])

  return {
    backendStatus,
    isRetrying,
    retryConnection,
  }
}
