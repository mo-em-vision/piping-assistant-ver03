import type { ReactNode } from 'react'

import './ComposerInput.css'

interface ComposerInputProps {
  disabled?: boolean
  submitting?: boolean
  canSubmit?: boolean
  placeholder?: string
  onSubmit: () => void
  children: ReactNode
  submitLabel?: string
  variant?: 'default' | 'underlined'
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

export function ComposerInput({
  disabled,
  submitting,
  canSubmit = true,
  placeholder,
  onSubmit,
  children,
  submitLabel = 'Submit',
  variant = 'default',
}: ComposerInputProps) {
  return (
    <div className="composer-input">
      <form
        className={`composer-input__shell${variant === 'underlined' ? ' composer-input__shell--underlined' : ''}`}
        onSubmit={(event) => {
          event.preventDefault()
          if (!disabled && !submitting && canSubmit) {
            onSubmit()
          }
        }}
      >
        <div className="composer-input__field-wrap">
          {children}
          {!children && placeholder ? (
            <textarea
              className="composer-input__field"
              placeholder={placeholder}
              disabled
              rows={1}
              readOnly
            />
          ) : null}
        </div>
        <button
          type="submit"
          className="composer-input__submit"
          disabled={disabled || submitting || !canSubmit}
          aria-label={submitting ? 'Submitting' : submitLabel}
          title={submitLabel}
        >
          <ArrowUpIcon />
        </button>
      </form>
    </div>
  )
}
