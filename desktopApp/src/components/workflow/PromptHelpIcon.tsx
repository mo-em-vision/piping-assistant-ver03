import { useId, useState } from 'react'

import './PromptHelpIcon.css'

interface PromptHelpIconProps {
  helpText: string
}

export function PromptHelpIcon({ helpText }: PromptHelpIconProps) {
  const tooltipId = useId()
  const [open, setOpen] = useState(false)
  const trimmed = helpText.trim()
  if (!trimmed) {
    return null
  }

  return (
    <span className="prompt-help-icon">
      <button
        type="button"
        className="prompt-help-icon__button"
        aria-label="Show input guidance"
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        ?
      </button>
      {open ? (
        <span id={tooltipId} role="tooltip" className="prompt-help-icon__tooltip">
          {trimmed}
        </span>
      ) : null}
    </span>
  )
}
