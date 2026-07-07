interface PhaseBadgeProps {
  phase: string
  taskStatus: string
}

function formatLabel(value: string): string {
  return value.replace(/_/g, ' ')
}

export default function PhaseBadge({ phase, taskStatus }: PhaseBadgeProps) {
  return (
    <div className="phase-badge">
      <span className="phase-badge__label">Phase</span>
      <strong>{formatLabel(phase)}</strong>
      <span className="phase-badge__divider">·</span>
      <span className="phase-badge__status">{formatLabel(taskStatus)}</span>
    </div>
  )
}
