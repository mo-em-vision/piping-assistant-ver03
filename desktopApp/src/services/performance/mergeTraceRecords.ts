import type { PerformanceSpanDto, PerformanceTraceDto } from '@/types/backend/inspection'

const MAX_SPANS_PER_TRACE = 80
const MAX_NOTE_LEN = 120

function sanitizeNotes(notes: string | null | undefined): string | null {
  if (!notes) {
    return null
  }
  const text = notes.trim().replace(/\s+/g, ' ')
  if (!text) {
    return null
  }
  return text.length > MAX_NOTE_LEN ? `${text.slice(0, MAX_NOTE_LEN - 3)}...` : text
}

function mergeSpans(
  frontendSpans: PerformanceSpanDto[] | null | undefined,
  backendSpans: PerformanceSpanDto[] | null | undefined,
): { spans: PerformanceSpanDto[]; omitted: number } {
  const merged = new Map<string, PerformanceSpanDto>()
  for (const span of frontendSpans ?? []) {
    merged.set(span.span_id, span)
  }
  for (const span of backendSpans ?? []) {
    merged.set(span.span_id, span)
  }
  const spans = [...merged.values()]
  if (spans.length <= MAX_SPANS_PER_TRACE) {
    return { spans, omitted: 0 }
  }
  const kept = spans.slice(0, MAX_SPANS_PER_TRACE)
  return { spans: kept, omitted: spans.length - kept.length }
}

export function mergeTraceRecords(
  frontend: PerformanceTraceDto,
  backend: PerformanceTraceDto,
): PerformanceTraceDto {
  const { spans, omitted } = mergeSpans(frontend.spans, backend.spans)
  return {
    trace_id: backend.trace_id || frontend.trace_id,
    trigger: backend.trigger || frontend.trigger,
    task_id: backend.task_id ?? frontend.task_id,
    total_duration_ms: Math.max(frontend.total_duration_ms, backend.total_duration_ms),
    llm_call_occurred: frontend.llm_call_occurred || backend.llm_call_occurred,
    status: backend.status !== 'running' ? backend.status : frontend.status,
    error: backend.error ?? frontend.error,
    spans_omitted: (backend.spans_omitted ?? 0) + (frontend.spans_omitted ?? 0) + omitted,
    spans,
  }
}

export function createFrontendSpan(
  name: string,
  durationMs: number,
  options: { status?: string; notes?: string | null } = {},
): PerformanceSpanDto {
  const { status = 'success', notes } = options
  const spanId = crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  return {
    span_id: spanId,
    parent_span_id: null,
    name,
    op_type: 'frontend',
    duration_ms: Math.max(0, Math.round(durationMs * 10) / 10),
    status,
    llm: false,
    notes: sanitizeNotes(notes ?? null),
  }
}
