export function asString(value: unknown): string | null {
  if (value == null || value === '') {
    return null
  }
  return String(value)
}

export function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => String(item)).filter(Boolean)
}
