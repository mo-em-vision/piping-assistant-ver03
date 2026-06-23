import type { ApiErrorBody, ApiRecoveryInfo } from '@/types/backend/api'

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details?: Record<string, unknown>
  readonly recovery?: ApiRecoveryInfo

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.code = body.code
    this.status = status
    this.details = body.details
    this.recovery = body.recovery
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
