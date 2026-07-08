export const PERFORMANCE_TRACE_HEADER = 'X-Performance-Trace-Id'

const TRACE_ID_PATTERN = /^[0-9a-f]{16}$/

export function generateTraceId(): string {
  const bytes = new Uint8Array(8)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function normalizeTraceId(value: string | null | undefined): string | null {
  if (!value) {
    return null
  }
  const cleaned = value.trim().toLowerCase()
  return TRACE_ID_PATTERN.test(cleaned) ? cleaned : null
}
