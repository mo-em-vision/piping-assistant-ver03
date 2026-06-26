const HIDDEN_UNITS = new Set(['dimensionless', ''])

function formatUnitForDisplay(unit: string): string {
  const normalized = unit.trim().toLowerCase()
  if (normalized === 'c') {
    return '°C'
  }
  if (normalized === 'f') {
    return '°F'
  }
  if (normalized === 'k') {
    return 'K'
  }
  return unit
}

function formatScalar(value: number): string {
  return Number.parseFloat(value.toPrecision(6)).toString()
}

export function formatEngineeringDisplayValue(value: unknown, unit?: string | null): string {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }

  if (unit && !HIDDEN_UNITS.has(unit)) {
    if (unit === 'Pa' && typeof value === 'number') {
      return `${formatScalar(value / 1_000_000)} MPa`
    }
    return `${String(value)} ${formatUnitForDisplay(unit)}`
  }

  return String(value)
}
