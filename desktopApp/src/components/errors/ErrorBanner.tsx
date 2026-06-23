import type { UserFacingError } from '@/types/frontend/userError'

import './ErrorBanner.css'

interface ErrorBannerProps {
  error: UserFacingError
  onRetry?: () => void
  onDismiss?: () => void
  compact?: boolean
  retryLabel?: string
  className?: string
}

export function ErrorBanner({
  error,
  onRetry,
  onDismiss,
  compact = false,
  retryLabel = 'Retry',
  className = '',
}: ErrorBannerProps) {
  const showRetry = error.retryable && onRetry

  return (
    <div
      className={`error-banner${compact ? ' error-banner--compact' : ''}${className ? ` ${className}` : ''}`}
      role="alert"
    >
      <div className="error-banner__header">
        <p className="error-banner__title">{error.title}</p>
        {onDismiss ? (
          <button type="button" className="error-banner__dismiss" onClick={onDismiss} aria-label="Dismiss error">
            ×
          </button>
        ) : null}
      </div>

      {!compact ? (
        <dl className="error-banner__details">
          <div>
            <dt>What happened</dt>
            <dd>{error.whatHappened}</dd>
          </div>
          <div>
            <dt>Possible reason</dt>
            <dd>{error.possibleReason}</dd>
          </div>
          <div>
            <dt>Next action</dt>
            <dd>{error.nextAction}</dd>
          </div>
          {error.affectedParameter ? (
            <div>
              <dt>Affected parameter</dt>
              <dd>
                <code>{error.affectedParameter}</code>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="error-banner__summary">{error.nextAction}</p>
      )}

      {showRetry ? (
        <div className="error-banner__actions">
          <button type="button" className="error-banner__retry" onClick={onRetry}>
            {retryLabel}
          </button>
        </div>
      ) : null}
    </div>
  )
}
