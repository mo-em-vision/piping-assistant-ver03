import type { ParameterOptionDto } from '@/types/backend/parameters'

interface DropdownInputProps {
  value: string
  options: ParameterOptionDto[]
  onChange: (value: string) => void
  disabled?: boolean
}

export function DropdownInput({ value, options, onChange, disabled }: DropdownInputProps) {
  return (
    <select
      className="parameter-control"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
    >
      <option value="">Select…</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
