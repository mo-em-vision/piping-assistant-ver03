import { useCallback, useEffect, useState } from 'react'

import { inspectionApi } from '@/services/api/inspectionApi'

import type { DevOperationsSnapshotDto } from '@/types/backend/inspection'

const EMPTY_SNAPSHOT: DevOperationsSnapshotDto = { running: [], recent: [] }

export function useOperationTracker(pollMs = 500) {
  const [snapshot, setSnapshot] = useState<DevOperationsSnapshotDto>(EMPTY_SNAPSHOT)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await inspectionApi.getOperations()
      setSnapshot(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation tracking unavailable')
      setSnapshot(EMPTY_SNAPSHOT)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    const timer = window.setInterval(() => {
      void reload()
    }, pollMs)
    return () => {
      window.clearInterval(timer)
    }
  }, [pollMs, reload])

  return { snapshot, error, loading, reload }
}
