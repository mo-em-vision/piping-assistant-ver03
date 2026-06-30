import type { BackendStatusPayload } from '@/config/constants'
import { constants } from '@/config/constants'
import { env } from '@/config/env'
import { useInspectorStore } from '@/components/dev/inspector/inspectorStore'

import './AppHeader.css'

function statusLabel(status: BackendStatusPayload['status']): string {
  switch (status) {
    case 'connected':
      return 'Connected'
    case 'starting':
      return 'Connecting…'
    case 'error':
      return 'Unavailable'
    default:
      return 'Stopped'
  }
}

interface AppHeaderProps {
  backendStatus: BackendStatusPayload
  isRetrying: boolean
  onRetry: () => void
}

export function AppHeader({ backendStatus, isRetrying, onRetry }: AppHeaderProps) {
  const inspectorOpen = useInspectorStore((state) => state.open)
  const toggleInspector = useInspectorStore((state) => state.toggleOpen)

  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__name">{env.appName || constants.appName}</span>
        {env.devMode ? <span className="app-header__badge">Dev</span> : null}
        {env.devMode ? (
          <button type="button" className="app-header__inspector-toggle" onClick={toggleInspector}>
            {inspectorOpen ? 'Hide Inspector' : 'Inspector'}
          </button>
        ) : null}
      </div>

      <div className="app-header__status">
        <span className={`status-pill status-pill--${backendStatus.status}`}>
          {statusLabel(backendStatus.status)}
        </span>
        {backendStatus.status === 'error' ? (
          <button
            type="button"
            className="app-header__retry"
            onClick={onRetry}
            disabled={isRetrying}
          >
            {isRetrying ? 'Retrying…' : 'Retry'}
          </button>
        ) : null}
      </div>
    </header>
  )
}
