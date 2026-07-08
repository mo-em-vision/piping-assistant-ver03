import { useEffect } from 'react'

import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

function roundMs(value: number): number {
  return Math.round(value * 10) / 10
}

export function useDevRenderSpan(spanName: string, enabled = true, deps: unknown[] = []) {
  const activeTraceId = usePerformanceTraceStore((state) => state.activeTraceId)

  useEffect(() => {
    if (!enabled || !activeTraceId) {
      return
    }

    const trace = usePerformanceTraceStore.getState().getTrace(activeTraceId)
    if (!trace || trace.trigger === 'inspection_poll') {
      return
    }

    const renderStarted = performance.now()
    let cancelled = false

    const frame = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (cancelled) {
          return
        }
        usePerformanceTraceStore.getState().recordFrontendSpan(activeTraceId, {
          name: spanName,
          duration_ms: roundMs(performance.now() - renderStarted),
        })
      })
    })

    return () => {
      cancelled = true
      window.cancelAnimationFrame(frame)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller controls extra deps
  }, [spanName, enabled, activeTraceId, ...deps])
}
