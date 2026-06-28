import type { StatusVariant } from '@/types/frontend/taskState'

type PinnedTabKind = 'task' | 'chat' | 'standards'

export function pinnedTabAriaLabel(kind: PinnedTabKind, statusLabel?: string): string {
  if (kind === 'chat') {
    return 'Chat'
  }
  if (kind === 'standards') {
    return 'Standards'
  }
  return statusLabel ? `Task — ${statusLabel}` : 'Task'
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5.25 8.1 7 9.85 10.75 6.1"
      />
    </svg>
  )
}

function AlertCircleIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <path fill="currentColor" d="M8 4.75a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4.75Zm0 7.5a.875.875 0 1 0 0-1.75.875.875 0 0 0 0 1.75Z" />
    </svg>
  )
}

function ProgressRingIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.25" opacity="0.35" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M8 1.75a6.25 6.25 0 0 1 0 12.5"
      />
    </svg>
  )
}

function XCircleIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M5.75 5.75 10.25 10.25M10.25 5.75 5.75 10.25"
      />
    </svg>
  )
}

function ClipboardIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
        d="M5.5 2.75h5l.75 1.25H12a1 1 0 0 1 1 1v8.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h.75L5.5 2.75Z"
      />
      <path fill="none" stroke="currentColor" strokeWidth="1.25" d="M6 5.5h4" />
    </svg>
  )
}

function taskIconForVariant(variant: StatusVariant) {
  switch (variant) {
    case 'success':
      return <CheckCircleIcon />
    case 'warning':
      return <AlertCircleIcon />
    case 'info':
      return <ProgressRingIcon />
    case 'error':
      return <XCircleIcon />
    default:
      return <ClipboardIcon />
  }
}

interface TaskTabIconProps {
  variant: StatusVariant
}

export function TaskTabIcon({ variant }: TaskTabIconProps) {
  return (
    <span className={`side-panel__tab-icon side-panel__tab-icon--${variant}`}>
      {taskIconForVariant(variant)}
    </span>
  )
}

function MessageBubbleIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
        d="M3.25 3.25h9.5a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H7.5L4.5 13V10.75H3.25a1 1 0 0 1-1-1v-5.5a1 1 0 0 1 1-1Z"
      />
    </svg>
  )
}

export function ChatTabIcon() {
  return (
    <span className="side-panel__tab-icon side-panel__tab-icon--chat">
      <MessageBubbleIcon />
    </span>
  )
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        d="M10.25 10.25 14 14"
      />
    </svg>
  )
}

export function StandardsTabIcon() {
  return (
    <span className="side-panel__tab-icon side-panel__tab-icon--standards">
      <SearchIcon />
    </span>
  )
}
