interface TextInputProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
}

export function TextInput({ value, onChange, disabled, placeholder }: TextInputProps) {
  return (
    <input
      className="parameter-control"
      type="text"
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
    />
  )
}
