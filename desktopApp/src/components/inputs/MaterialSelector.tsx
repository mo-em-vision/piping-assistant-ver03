import { MaterialSearchInput } from '@/components/workflow/MaterialSearchInput'

interface MaterialSelectorProps {
  value: string
  onChange: (value: string) => void
  onSubmit?: (value?: string) => void
  disabled?: boolean
  submitting?: boolean
}

export function MaterialSelector({
  value,
  onChange,
  onSubmit,
  disabled,
  submitting,
}: MaterialSelectorProps) {
  return (
    <MaterialSearchInput
      value={value}
      onChange={onChange}
      onSubmit={(nextValue) => onSubmit?.(nextValue)}
      disabled={disabled}
      submitting={submitting}
    />
  )
}
