import type { StatusVariant } from '@/types/frontend/taskState'

import './StatusIndicator.css'

const LABELS: Record<StatusVariant, string> = {
  success: 'Completed',
  warning: 'Awaiting input',
  info: 'In progress',
  neutral: 'Idle',
  error: 'Invalidated',
}

interface StatusIndicatorProps {
  label?: string
  variant: StatusVariant
}

export function StatusIndicator({ label, variant }: StatusIndicatorProps) {
  return (
    <span className={`status-indicator status-indicator--${variant}`}>
      {label ?? LABELS[variant]}
    </span>
  )
}
