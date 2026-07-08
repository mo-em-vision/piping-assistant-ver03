export const NOT_AVAILABLE = 'not available'

export function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return NOT_AVAILABLE
  }
  if (typeof value === 'string' && value.trim() === '') {
    return NOT_AVAILABLE
  }
  return String(value)
}
