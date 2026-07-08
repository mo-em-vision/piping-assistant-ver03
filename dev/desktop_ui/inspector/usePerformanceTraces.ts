import { useCallback, useEffect, useMemo, useState } from 'react'

import { mergeTraceRecords } from '@/services/performance/mergeTraceRecords'
import { inspectionApi } from '@/services/api/inspectionApi'
import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

import type { PerformanceTraceDto } from '@/types/backend/inspection'

function mergeAllTraces(
  storeTraces: PerformanceTraceDto[],
  polled: PerformanceTraceDto[],
): PerformanceTraceDto[] {
  const byId = new Map<string, PerformanceTraceDto>()
  for (const trace of polled) {
    byId.set(trace.trace_id, trace)
  }
  for (const trace of storeTraces) {
    const existing = byId.get(trace.trace_id)
    byId.set(trace.trace_id, existing ? mergeTraceRecords(trace, existing) : trace)
  }
  return [...byId.values()].sort((left, right) => right.total_duration_ms - left.total_duration_ms)
}

export function usePerformanceTraces(pollMs = 2000) {
  const traceOrder = usePerformanceTraceStore((state) => state.traceOrder)
  const tracesById = usePerformanceTraceStore((state) => state.tracesById)
  const storeTraces = useMemo(
    () =>
      traceOrder
        .map((traceId) => tracesById[traceId])
        .filter((trace): trace is PerformanceTraceDto => Boolean(trace)),
    [traceOrder, tracesById],
  )

  const [polledTraces, setPolledTraces] = useState<PerformanceTraceDto[]>([])
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const traces = useMemo(
    () => mergeAllTraces(storeTraces, polledTraces),
    [storeTraces, polledTraces],
  )

  const selectedTrace = useMemo(() => {
    if (!traces.length) {
      return null
    }
    if (selectedTraceId) {
      const match = traces.find((trace) => trace.trace_id === selectedTraceId)
      if (match) {
        return match
      }
    }
    return traces[0]
  }, [selectedTraceId, traces])

  useEffect(() => {
    if (!selectedTraceId && traces[0]?.trace_id) {
      setSelectedTraceId(traces[0].trace_id)
    }
  }, [selectedTraceId, traces])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await inspectionApi.getPerformanceTraces()
      const tracesFromApi = Array.isArray(data.traces) ? data.traces : []
      setPolledTraces(tracesFromApi)
      usePerformanceTraceStore.getState().ingestPolledTraces(tracesFromApi)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Performance tracing unavailable')
      setPolledTraces([])
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

  return {
    traces,
    selectedTrace,
    selectedTraceId,
    setSelectedTraceId,
    error,
    loading,
    reload,
  }
}
