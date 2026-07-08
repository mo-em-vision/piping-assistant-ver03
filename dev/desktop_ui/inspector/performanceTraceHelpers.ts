import type { PerformanceSpanDto } from '@/types/backend/inspection'

export type DurationSeverity = 'normal' | 'watch' | 'slow' | 'critical'

export function durationSeverity(durationMs: number | null | undefined): DurationSeverity {
  if (durationMs == null || Number.isNaN(durationMs)) {
    return 'normal'
  }
  if (durationMs >= 1000) {
    return 'critical'
  }
  if (durationMs >= 500) {
    return 'slow'
  }
  if (durationMs >= 100) {
    return 'watch'
  }
  return 'normal'
}

export function severityClassName(severity: DurationSeverity): string {
  return `perf-trace-row--${severity}`
}

export function formatDurationMs(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '—'
  }
  if (value < 1000) {
    return `${value.toFixed(1)} ms`
  }
  return `${(value / 1000).toFixed(2)} s`
}

export function triggerLabel(trigger: string): string {
  if (trigger === 'inspection_poll') {
    return 'Inspection poll'
  }
  return trigger
}

export function isInspectionPollTrace(trigger: string): boolean {
  return trigger === 'inspection_poll'
}

export function spanDepth(
  span: PerformanceSpanDto,
  spanById: Map<string, PerformanceSpanDto>,
): number {
  let depth = 0
  let parentId = span.parent_span_id
  const seen = new Set<string>()
  while (parentId) {
    if (seen.has(parentId)) {
      break
    }
    seen.add(parentId)
    depth += 1
    parentId = spanById.get(parentId)?.parent_span_id ?? null
  }
  return depth
}

export function sortedSpans(spans: PerformanceSpanDto[]): PerformanceSpanDto[] {
  return [...spans].sort((left, right) => {
    if (left.duration_ms !== right.duration_ms) {
      return right.duration_ms - left.duration_ms
    }
    return left.name.localeCompare(right.name)
  })
}
