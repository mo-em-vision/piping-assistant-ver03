import { type KeyboardEvent } from 'react'

import { UnitPillGroup } from '@/components/inputs/UnitPillGroup'

import './ComposerInlineInput.css'

interface ComposerInlineInputProps {
  value: string
  onChange: (value: string) => void
  placeholder: string
  disabled?: boolean
  submitting?: boolean
  canSubmit?: boolean
  onSubmit: () => void
  inputMode?: 'text' | 'decimal' | 'search'
  units?: string[]
  unit?: string
  onUnitChange?: (unit: string) => void
  unitAriaLabel?: string
  variant?: 'text' | 'numeric'
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void
}

function ArrowUpIcon() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
      <path
        fill="currentColor"
        d="M8 1.75 2.75 7l1.35 1.35L7 5.45V14h2V5.45l3.9 3.9L14.25 7 8 1.75Z"
      />
    </svg>
  )
}

export function ComposerInlineInput({
  value,
  onChange,
  placeholder,
  disabled,
  submitting,
  canSubmit = true,
  onSubmit,
  inputMode = 'text',
  units,
  unit,
  onUnitChange,
  unitAriaLabel,
  variant = 'text',
  onKeyDown,
}: ComposerInlineInputProps) {
  const busy = Boolean(disabled || submitting)
  const showUnits = Boolean(units && units.length > 0 && unit && onUnitChange)

  return (
    <form
      className={`composer-inline-row composer-inline-row--${variant}`}
      onSubmit={(event) => {
        event.preventDefault()
        if (!busy && canSubmit) {
          onSubmit()
        }
      }}
    >
      <input
        className="composer-inline-row__value"
        type="text"
        inputMode={inputMode}
        value={value}
        placeholder={placeholder}
        disabled={busy}
        aria-label={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          onKeyDown?.(event)
          if (event.defaultPrevented) {
            return
          }
          if (event.key === 'Enter') {
            event.preventDefault()
            if (!busy && canSubmit) {
              onSubmit()
            }
          }
        }}
      />
      {showUnits ? (
        <UnitPillGroup
          units={units!}
          value={unit!}
          onChange={onUnitChange!}
          disabled={busy}
          aria-label={unitAriaLabel ?? 'Unit'}
        />
      ) : null}
      <button
        type="submit"
        className="composer-inline-row__submit"
        disabled={busy || !canSubmit}
        aria-label={submitting ? 'Submitting' : 'Submit'}
        title="Submit"
      >
        <ArrowUpIcon />
      </button>
    </form>
  )
}
