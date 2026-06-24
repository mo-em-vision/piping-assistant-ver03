import { CheckboxInput } from './CheckboxInput'
import { DropdownInput } from './DropdownInput'
import { MaterialSelector } from './MaterialSelector'
import { MultiSelectInput } from './MultiSelectInput'
import { NumberInput } from './NumberInput'
import { TextInput } from './TextInput'

import type { ParameterDefinitionDto } from '@/types/backend/parameters'

import './ParameterForm.css'

interface ParameterInputProps {
  parameter: ParameterDefinitionDto
  value: unknown
  unit: string
  onValueChange: (value: unknown) => void
  onUnitChange: (unit: string) => void
  disabled?: boolean
  hideUnitSelector?: boolean
  placeholder?: string
}

export function ParameterInput({
  parameter,
  value,
  unit,
  onValueChange,
  onUnitChange,
  disabled,
  hideUnitSelector,
  placeholder,
}: ParameterInputProps) {
  switch (parameter.type) {
    case 'number':
      return (
        <NumberInput
          value={value === null || value === undefined ? '' : String(value)}
          unit={unit}
          units={parameter.units}
          onValueChange={(next) => onValueChange(next)}
          onUnitChange={onUnitChange}
          disabled={disabled}
          hideUnitSelector={hideUnitSelector}
          placeholder={placeholder}
        />
      )
    case 'checkbox':
      return (
        <CheckboxInput
          checked={Boolean(value)}
          label={parameter.label}
          onChange={onValueChange}
          disabled={disabled}
        />
      )
    case 'dropdown':
      return (
        <DropdownInput
          value={value == null ? '' : String(value)}
          options={parameter.options ?? []}
          onChange={onValueChange}
          disabled={disabled}
        />
      )
    case 'multi_select':
      return (
        <MultiSelectInput
          values={Array.isArray(value) ? value.map(String) : []}
          options={parameter.options ?? []}
          onChange={onValueChange}
          disabled={disabled}
        />
      )
    case 'material':
      return (
        <MaterialSelector
          value={value == null ? '' : String(value)}
          onChange={onValueChange}
          disabled={disabled}
        />
      )
    case 'unit':
      return (
        <NumberInput
          value={value === null || value === undefined ? '' : String(value)}
          unit={unit}
          units={parameter.units}
          onValueChange={(next) => onValueChange(next)}
          onUnitChange={onUnitChange}
          disabled={disabled}
          hideUnitSelector={hideUnitSelector}
          placeholder={placeholder}
        />
      )
    case 'text':
    default:
      return (
        <TextInput
          value={value == null ? '' : String(value)}
          onChange={onValueChange}
          disabled={disabled}
        />
      )
  }
}
