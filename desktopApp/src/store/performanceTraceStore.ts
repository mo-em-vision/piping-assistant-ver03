import { create } from 'zustand'

import { createFrontendSpan, mergeTraceRecords } from '@/services/performance/mergeTraceRecords'
import { generateTraceId } from '@/services/performance/traceId'

import type { PerformanceTraceDto } from '@/types/backend/inspection'

const MAX_RECENT_TRACES = 40
const MAX_SPANS_PER_TRACE = 80

const startedAtByTraceId = new Map<string, number>()
const finalizeTimers = new Map<string, number>()

function roundMs(value: number): number {
  return Math.round(value * 10) / 10
}

function emptyTrace(traceId: string, trigger: string, taskId?: string | null): PerformanceTraceDto {
  return {
    trace_id: traceId,
    trigger,
    task_id: taskId ?? null,
    total_duration_ms: 0,
    llm_call_occurred: false,
    status: 'running',
    error: null,
    spans_omitted: 0,
    spans: [],
  }
}

function updateTotalDuration(trace: PerformanceTraceDto): PerformanceTraceDto {
  const startedAt = startedAtByTraceId.get(trace.trace_id)
  if (startedAt == null) {
    return trace
  }
  return {
    ...trace,
    total_duration_ms: roundMs(performance.now() - startedAt),
  }
}

function pushTraceOrder(order: string[], traceId: string): string[] {
  const next = [traceId, ...order.filter((id) => id !== traceId)]
  return next.slice(0, MAX_RECENT_TRACES)
}

interface PerformanceTraceStoreState {
  tracesById: Record<string, PerformanceTraceDto>
  traceOrder: string[]
  activeTraceId: string | null
  beginInteraction: (trigger: string, taskId?: string | null) => string
  ensureTrace: (traceId: string, trigger: string, taskId?: string | null, preserveActiveTrace?: boolean) => void
  setActiveTraceId: (traceId: string | null) => void
  recordFrontendSpan: (
    traceId: string,
    span: {
      name: string
      duration_ms: number
      status?: string
      notes?: string | null
    },
  ) => void
  mergeBackendTrace: (backend: PerformanceTraceDto | null | undefined) => void
  ingestPolledTraces: (traces: PerformanceTraceDto[]) => void
  scheduleFinalize: (traceId: string, status?: string, error?: string | null) => void
  finalizeTrace: (traceId: string, status?: string, error?: string | null) => void
  getTraces: () => PerformanceTraceDto[]
  getTrace: (traceId: string) => PerformanceTraceDto | undefined
  reset: () => void
}

export const usePerformanceTraceStore = create<PerformanceTraceStoreState>((set, get) => ({
  tracesById: {},
  traceOrder: [],
  activeTraceId: null,

  beginInteraction(trigger, taskId) {
    const traceId = generateTraceId()
    startedAtByTraceId.set(traceId, performance.now())
    const trace = emptyTrace(traceId, trigger, taskId)
    set((state) => ({
      activeTraceId: traceId,
      tracesById: { ...state.tracesById, [traceId]: trace },
      traceOrder: pushTraceOrder(state.traceOrder, traceId),
    }))
    return traceId
  },

  ensureTrace(traceId, trigger, taskId, preserveActiveTrace = false) {
    if (get().tracesById[traceId]) {
      if (!startedAtByTraceId.has(traceId)) {
        startedAtByTraceId.set(traceId, performance.now())
      }
      if (!preserveActiveTrace) {
        set({ activeTraceId: traceId })
      }
      return
    }
    startedAtByTraceId.set(traceId, performance.now())
    const trace = emptyTrace(traceId, trigger, taskId)
    set((state) => ({
      activeTraceId: preserveActiveTrace ? state.activeTraceId : traceId,
      tracesById: { ...state.tracesById, [traceId]: trace },
      traceOrder: pushTraceOrder(state.traceOrder, traceId),
    }))
  },

  setActiveTraceId(traceId) {
    set({ activeTraceId: traceId })
  },

  recordFrontendSpan(traceId, span) {
    set((state) => {
      const existing = state.tracesById[traceId]
      if (!existing) {
        return state
      }
      if (existing.spans.length >= MAX_SPANS_PER_TRACE) {
        const updated = updateTotalDuration({
          ...existing,
          spans_omitted: existing.spans_omitted + 1,
        })
        return {
          tracesById: { ...state.tracesById, [traceId]: updated },
        }
      }
      const nextSpan = createFrontendSpan(span.name, span.duration_ms, {
        status: span.status ?? 'success',
        notes: span.notes,
      })
      const updated = updateTotalDuration({
        ...existing,
        spans: [...existing.spans, nextSpan],
      })
      return {
        tracesById: { ...state.tracesById, [traceId]: updated },
      }
    })
  },

  mergeBackendTrace(backend) {
    if (!backend?.trace_id) {
      return
    }
    set((state) => {
      const existing = state.tracesById[backend.trace_id]
      const merged = existing ? mergeTraceRecords(existing, backend) : backend
      const isPollTrace = merged.trigger === 'inspection_poll'
      return {
        tracesById: { ...state.tracesById, [backend.trace_id]: updateTotalDuration(merged) },
        traceOrder: pushTraceOrder(state.traceOrder, backend.trace_id),
        activeTraceId: isPollTrace
          ? state.activeTraceId
          : (state.activeTraceId ?? backend.trace_id),
      }
    })
  },

  ingestPolledTraces(traces) {
    if (!traces?.length) {
      return
    }
    set((state) => {
      const tracesById = { ...state.tracesById }
      let traceOrder = [...state.traceOrder]
      for (const backend of traces) {
        const existing = tracesById[backend.trace_id]
        tracesById[backend.trace_id] = existing
          ? mergeTraceRecords(existing, backend)
          : backend
        traceOrder = pushTraceOrder(traceOrder, backend.trace_id)
      }
      return { tracesById, traceOrder }
    })
  },

  scheduleFinalize(traceId, status = 'success', error = null) {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        get().finalizeTrace(traceId, status, error)
      })
    })
  },

  finalizeTrace(traceId, status = 'success', error = null) {
    const existingTimer = finalizeTimers.get(traceId)
    if (existingTimer != null) {
      window.clearTimeout(existingTimer)
      finalizeTimers.delete(traceId)
    }
    set((state) => {
      const existing = state.tracesById[traceId]
      if (!existing) {
        return state
      }
      const finalized = updateTotalDuration({
        ...existing,
        status,
        error,
      })
      startedAtByTraceId.delete(traceId)
      return {
        tracesById: { ...state.tracesById, [traceId]: finalized },
        activeTraceId: state.activeTraceId === traceId ? null : state.activeTraceId,
      }
    })
  },

  getTraces() {
    const { traceOrder, tracesById } = get()
    return traceOrder
      .map((traceId) => tracesById[traceId])
      .filter((trace): trace is PerformanceTraceDto => Boolean(trace))
  },

  getTrace(traceId) {
    return get().tracesById[traceId]
  },

  reset() {
    startedAtByTraceId.clear()
    for (const timer of finalizeTimers.values()) {
      window.clearTimeout(timer)
    }
    finalizeTimers.clear()
    set({
      tracesById: {},
      traceOrder: [],
      activeTraceId: null,
    })
  },
}))
