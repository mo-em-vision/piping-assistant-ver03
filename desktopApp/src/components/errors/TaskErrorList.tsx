import { ErrorBanner } from '@/components/errors/ErrorBanner'
import { fromApiErrorBody } from '@/services/errors/errorMapper'
import type { ApiErrorBody } from '@/types/backend/api'

interface TaskErrorListProps {
  errors: ApiErrorBody[]
  onRefresh?: () => void
}

export function TaskErrorList({ errors, onRefresh }: TaskErrorListProps) {
  if (errors.length === 0) {
    return null
  }

  return (
    <div className="task-error-list">
      {errors.map((item, index) => {
        const userError = fromApiErrorBody(item)
        return (
          <ErrorBanner
            key={`${item.code}-${index}`}
            error={userError}
            onRetry={userError.retryable ? onRefresh : undefined}
            retryLabel="Refresh task"
          />
        )
      })}
    </div>
  )
}
