import { TextInput } from './TextInput'

interface MaterialSelectorProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function MaterialSelector({ value, onChange, disabled }: MaterialSelectorProps) {
  return (
    <TextInput
      value={value}
      onChange={onChange}
      disabled={disabled}
      placeholder="e.g. SA-106B"
    />
  )
}
