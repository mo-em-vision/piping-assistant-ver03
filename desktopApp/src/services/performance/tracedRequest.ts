import { backendClient } from '@/services/api/backendClient'
import type { RequestOptions } from '@/services/api/backendClient'
import { usePerformanceTraceStore } from '@/store/performanceTraceStore'

import type { PerformanceTraceDto } from '@/types/backend/inspection'
import type { TaskStateDto } from '@/types/backend/api'

export type TracedRequestMeta = {
  traceId: string
  trigger: string
  taskId?: string | null
  preserveActiveTrace?: boolean
}

function roundMs(value: number): number {
  return Math.round(value * 10) / 10
}

function extractPerformanceTrace(payload: unknown): PerformanceTraceDto | null {
  if (!payload || typeof payload !== 'object' || !('performance_trace' in payload)) {
    return null
  }
  const trace = (payload as TaskStateDto).performance_trace
  return trace ?? null
}

export async function tracedRequest<T>(
  path: string,
  options: RequestOptions & { method?: string },
  meta: TracedRequestMeta,
): Promise<T> {
  const store = usePerformanceTraceStore.getState()
  store.ensureTrace(meta.traceId, meta.trigger, meta.taskId ?? null, meta.preserveActiveTrace)
  if (!meta.preserveActiveTrace) {
    store.setActiveTraceId(meta.traceId)
  }

  store.recordFrontendSpan(meta.traceId, {
    name: 'request_sent',
    duration_ms: 0,
    status: 'success',
    notes: options.method ?? 'GET',
  })

  const requestStarted = performance.now()
  try {
    const { data } = await backendClient.requestDetailed<T>(path, {
      ...options,
      performanceTraceId: meta.traceId,
    })

    store.recordFrontendSpan(meta.traceId, {
      name: 'response_received',
      duration_ms: roundMs(performance.now() - requestStarted),
      status: 'success',
    })

    const backendTrace = extractPerformanceTrace(data)
    if (backendTrace) {
      store.mergeBackendTrace(backendTrace)
    }

    if (meta.trigger === 'inspection_poll') {
      store.finalizeTrace(meta.traceId, 'success')
    }

    return data
  } catch (error) {
    store.recordFrontendSpan(meta.traceId, {
      name: 'response_received',
      duration_ms: roundMs(performance.now() - requestStarted),
      status: 'error',
      notes: error instanceof Error ? error.message : 'request failed',
    })
    store.finalizeTrace(
      meta.traceId,
      'error',
      error instanceof Error ? error.message : 'request failed',
    )
    throw error
  }
}
