import { useEffect, useId, useRef, useState } from 'react'

import type { ParameterOptionDto } from '@/types/backend/parameters'

import './ScrollSelectPicker.css'

const VISIBLE_OPTIONS = 5

interface ScrollSelectPickerProps {
  options: ParameterOptionDto[]
  value: string | null
  placeholder: string
  onSelect: (value: string) => void
  disabled?: boolean
  ariaLabel: string
}

export function ScrollSelectPicker({
  options,
  value,
  placeholder,
  onSelect,
  disabled,
  ariaLabel,
}: ScrollSelectPickerProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listId = useId()

  const selectedLabel =
    options.find((option) => option.value === value)?.label ?? null

  useEffect(() => {
    if (!open) {
      return
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [open])

  const handleSelect = (nextValue: string) => {
    setOpen(false)
    onSelect(nextValue)
  }

  return (
    <div ref={rootRef} className="scroll-select-picker">
      <button
        type="button"
        className="scroll-select-picker__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span
          className={
            selectedLabel
              ? 'scroll-select-picker__trigger-value'
              : 'scroll-select-picker__trigger-placeholder'
          }
        >
          {selectedLabel ?? placeholder}
        </span>
        <span className="scroll-select-picker__chevron" aria-hidden>
          ▾
        </span>
      </button>

      {open ? (
        <div
          id={listId}
          className="scroll-select-picker__menu"
          role="listbox"
          aria-label={ariaLabel}
          style={{ ['--scroll-select-visible-rows' as string]: VISIBLE_OPTIONS }}
        >
          {options.map((option) => {
            const selected = value === option.value
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={selected}
                className={`scroll-select-picker__option${selected ? ' scroll-select-picker__option--selected' : ''}`}
                disabled={disabled}
                onClick={() => handleSelect(option.value)}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
