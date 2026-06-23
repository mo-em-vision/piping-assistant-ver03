import type { BackendStatusPayload } from '@/config/constants'
import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { apiUnreachableError, backendUnavailableError } from '@/services/errors/errorMapper'
import { useConnectionStore } from '@/store/connectionStore'

import './ConnectionErrorBanner.css'

interface ConnectionErrorBannerProps {
  backendStatus: BackendStatusPayload
  isRetrying: boolean
  onRetryBackend: () => void
  onReloadWorkspace: () => void
}

export function ConnectionErrorBanner({
  backendStatus,
  isRetrying,
  onRetryBackend,
  onReloadWorkspace,
}: ConnectionErrorBannerProps) {
  const apiStatus = useConnectionStore((state) => state.apiStatus)
  const apiError = useConnectionStore((state) => state.apiError)
  const checkApiConnection = useConnectionStore((state) => state.checkApiConnection)

  if (backendStatus.status === 'connected' && apiStatus !== 'error') {
    return null
  }

  const error =
    backendStatus.status !== 'connected'
      ? backendUnavailableError(backendStatus.detail)
      : apiUnreachableError(apiError ?? 'API health check failed.')

  const handleRetry = () => {
    if (backendStatus.status !== 'connected') {
      onRetryBackend()
      return
    }

    void checkApiConnection().then((ok) => {
      if (ok) {
        onReloadWorkspace()
      }
    })
  }

  return (
    <div className="connection-error-banner">
      <ErrorBanner
        error={error}
        onRetry={handleRetry}
        retryLabel={isRetrying ? 'Retrying…' : 'Retry connection'}
      />
    </div>
  )
}
