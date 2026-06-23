import { UnitSelector } from './UnitSelector'

interface NumberInputProps {
  value: string
  unit: string
  units: string[]
  onValueChange: (value: string) => void
  onUnitChange: (unit: string) => void
  disabled?: boolean
}

export function NumberInput({
  value,
  unit,
  units,
  onValueChange,
  onUnitChange,
  disabled,
}: NumberInputProps) {
  return (
    <div className="parameter-field__row">
      <input
        className="parameter-control"
        type="number"
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        disabled={disabled}
      />
      <UnitSelector units={units} value={unit} onChange={onUnitChange} disabled={disabled} />
    </div>
  )
}
