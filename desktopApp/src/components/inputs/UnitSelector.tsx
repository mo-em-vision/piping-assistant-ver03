import { useEffect, useId, useRef, useState } from 'react'

import './UnitSelector.css'

interface UnitSelectorProps {
  units: string[]
  value: string
  onChange: (unit: string) => void
  disabled?: boolean
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
      <path
        fill="currentColor"
        d="M4.47 5.97a.75.75 0 0 1 1.06 0L8 8.44l2.47-2.47a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 0 1 0-1.06Z"
      />
    </svg>
  )
}

export function UnitSelector({ units, value, onChange, disabled }: UnitSelectorProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listboxId = useId()

  useEffect(() => {
    if (!open) {
      return
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [open])

  if (units.length === 0) {
    return null
  }

  const selectUnit = (unit: string) => {
    onChange(unit)
    setOpen(false)
  }

  return (
    <div
      ref={rootRef}
      className={`unit-selector${open ? ' unit-selector--open' : ''}${disabled ? ' unit-selector--disabled' : ''}`}
    >
      <button
        type="button"
        className="unit-selector__trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => {
          if (!disabled) {
            setOpen((current) => !current)
          }
        }}
      >
        <span className="unit-selector__value">{value}</span>
        <ChevronDownIcon />
      </button>
      {open ? (
        <ul id={listboxId} className="unit-selector__menu" role="listbox" aria-label="Unit">
          {units.map((unit) => (
            <li key={unit} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={unit === value}
                className={`unit-selector__option${unit === value ? ' unit-selector__option--selected' : ''}`}
                onClick={() => selectUnit(unit)}
              >
                {unit}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
