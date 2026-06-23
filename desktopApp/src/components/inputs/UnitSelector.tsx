interface UnitSelectorProps {
  units: string[]
  value: string
  onChange: (unit: string) => void
  disabled?: boolean
}

export function UnitSelector({ units, value, onChange, disabled }: UnitSelectorProps) {
  if (units.length === 0) {
    return null
  }

  return (
    <select
      className="parameter-control parameter-control--unit"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
      aria-label="Unit"
    >
      {units.map((unit) => (
        <option key={unit} value={unit}>
          {unit}
        </option>
      ))}
    </select>
  )
}
