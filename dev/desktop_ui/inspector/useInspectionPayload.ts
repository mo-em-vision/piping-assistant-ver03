import { useCallback, useEffect, useState } from 'react'

import { inspectionApi } from '@/services/api/inspectionApi'
import { getActiveSessionId } from '@/store/projectStore'
import { useTaskStore } from '@/store/taskStore'

import type { InspectionPayloadDto } from '@/types/backend/inspection'

export function useInspectionPayload(pollMs = 2000) {
  const activeTaskId = useTaskStore((state) => state.activeTask?.id ?? null)
  const storeSessionId = useTaskStore((state) => state.sessionId)
  const sessionId = storeSessionId ?? getActiveSessionId() ?? null
  const [payload, setPayload] = useState<InspectionPayloadDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    if (!activeTaskId) {
      setPayload(null)
      return
    }
    setLoading(true)
    try {
      const data = await inspectionApi.get(activeTaskId, sessionId ?? undefined)
      setPayload(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Inspection unavailable')
      setPayload(null)
    } finally {
      setLoading(false)
    }
  }, [activeTaskId, sessionId])

  useEffect(() => {
    if (!activeTaskId) {
      setPayload(null)
      return
    }

    void reload()
    const timer = window.setInterval(() => {
      void reload()
    }, pollMs)

    return () => {
      window.clearInterval(timer)
    }
  }, [activeTaskId, pollMs, reload])

  return { payload, error, loading, activeTaskId, sessionId, reload }
}
