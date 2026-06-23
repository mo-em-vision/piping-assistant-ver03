interface CheckboxInputProps {
  checked: boolean
  label: string
  onChange: (checked: boolean) => void
  disabled?: boolean
}

export function CheckboxInput({ checked, label, onChange, disabled }: CheckboxInputProps) {
  return (
    <label className="parameter-field__checkbox">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        disabled={disabled}
      />
      <span>{label}</span>
    </label>
  )
}
