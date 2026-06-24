import { type ReactNode } from 'react'

import './ExternalLink.css'

interface ExternalLinkProps {
  href: string
  children: ReactNode
  className?: string
  showBadge?: boolean
}

function ExternalLinkIcon() {
  return (
    <svg className="external-link__icon" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M6.25 3.5H12.5V9.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8.75 7.25L12.5 3.5M12.5 3.5H9M12.5 3.5V7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 5.5V12.25C4 12.6642 4.33579 13 4.75 13H11.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

function linkLabel(children: ReactNode): string {
  if (typeof children === 'string' || typeof children === 'number') {
    return String(children).trim()
  }
  return ''
}

export function ExternalLink({
  href,
  children,
  className,
  showBadge = true,
}: ExternalLinkProps) {
  const label = linkLabel(children)
  const ariaLabel = label ? `Opens external link: ${label}` : 'Opens external link'

  return (
    <a
      className={`external-link${className ? ` ${className}` : ''}`}
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      aria-label={ariaLabel}
    >
      <span className="external-link__label">{children}</span>
      {showBadge ? <span className="external-link__badge">External</span> : null}
      <ExternalLinkIcon />
    </a>
  )
}
