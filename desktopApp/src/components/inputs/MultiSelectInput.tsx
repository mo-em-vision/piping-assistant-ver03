import type { ParameterOptionDto } from '@/types/backend/parameters'

interface MultiSelectInputProps {
  values: string[]
  options: ParameterOptionDto[]
  onChange: (values: string[]) => void
  disabled?: boolean
}

export function MultiSelectInput({ values, options, onChange, disabled }: MultiSelectInputProps) {
  const toggle = (optionValue: string) => {
    if (values.includes(optionValue)) {
      onChange(values.filter((item) => item !== optionValue))
      return
    }
    onChange([...values, optionValue])
  }

  return (
    <div className="multi-select-options">
      {options.map((option) => (
        <label key={option.value} className="multi-select-option">
          <input
            type="checkbox"
            checked={values.includes(option.value)}
            onChange={() => toggle(option.value)}
            disabled={disabled}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  )
}
