import './UnitPillGroup.css'

interface UnitPillGroupProps {
  units: string[]
  value: string
  onChange: (unit: string) => void
  disabled?: boolean
  'aria-label'?: string
}

export function UnitPillGroup({
  units,
  value,
  onChange,
  disabled,
  'aria-label': ariaLabel = 'Unit',
}: UnitPillGroupProps) {
  if (units.length === 0) {
    return null
  }

  return (
    <div className="unit-pill-group" role="group" aria-label={ariaLabel}>
      {units.map((unit) => (
        <button
          key={unit}
          type="button"
          className={`unit-pill-group__pill${unit === value ? ' unit-pill-group__pill--active' : ''}`}
          aria-pressed={unit === value}
          disabled={disabled}
          onClick={() => onChange(unit)}
        >
          {unit}
        </button>
      ))}
    </div>
  )
}
