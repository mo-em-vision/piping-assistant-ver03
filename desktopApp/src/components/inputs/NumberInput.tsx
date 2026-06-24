import { UnitSelector } from './UnitSelector'

interface NumberInputProps {
  value: string
  unit: string
  units: string[]
  onValueChange: (value: string) => void
  onUnitChange: (unit: string) => void
  disabled?: boolean
  hideUnitSelector?: boolean
  placeholder?: string
}

export function NumberInput({
  value,
  unit,
  units,
  onValueChange,
  onUnitChange,
  disabled,
  hideUnitSelector,
  placeholder,
}: NumberInputProps) {
  return (
    <div className="parameter-field__row parameter-field__row--number">
      <input
        className="parameter-control parameter-control--number"
        type="number"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onValueChange(event.target.value)}
        disabled={disabled}
      />
      {hideUnitSelector ? null : (
        <UnitSelector units={units} value={unit} onChange={onUnitChange} disabled={disabled} />
      )}
    </div>
  )
}
