import { isApiError } from '@/types/backend/apiError'
import type { ApiErrorBody, ApiRecoveryInfo } from '@/types/backend/api'
import type { UserFacingError } from '@/types/frontend/userError'

const RETRYABLE_CODES = new Set([
  'backend_unavailable',
  'api_unreachable',
  'internal_error',
  'unknown_error',
  'not_found',
  'task_not_found',
  'project_not_found',
  'report_not_found',
  'calculation_failed',
  'invalid_response',
])

const CLIENT_GUIDANCE: Record<string, Pick<UserFacingError, 'title' | 'possibleReason' | 'nextAction'>> = {
  invalid_input: {
    title: 'Invalid engineering input',
    possibleReason: 'The submitted value failed validation or is outside allowed limits.',
    nextAction: 'Correct the parameter and submit again.',
  },
  invalid_request: {
    title: 'Request could not be processed',
    possibleReason: 'A required field was missing or formatted incorrectly.',
    nextAction: 'Review the form and try again.',
  },
  task_not_found: {
    title: 'Task not found',
    possibleReason: 'The task may have been removed or belongs to another project.',
    nextAction: 'Reload the workspace or select a different task.',
  },
  project_not_found: {
    title: 'Project not found',
    possibleReason: 'The selected project is no longer available in local storage.',
    nextAction: 'Choose another project or create a new one.',
  },
  report_not_found: {
    title: 'Report not available',
    possibleReason: 'The requested report file has not been generated yet.',
    nextAction: 'Generate the report, then retry the download or preview.',
  },
  calculation_failed: {
    title: 'Calculation failed',
    possibleReason: 'The engineering workflow stopped because inputs or assumptions became invalid.',
    nextAction: 'Review warnings, update inputs, and refresh the task.',
  },
  backend_unavailable: {
    title: 'Backend unavailable',
    possibleReason: 'The local engineering API is not running or cannot be reached.',
    nextAction: 'Retry the connection. If the problem continues, restart the desktop application.',
  },
  api_unreachable: {
    title: 'Cannot reach API',
    possibleReason: 'The desktop app could not complete a health check against the backend.',
    nextAction: 'Retry after confirming the Python API process is running.',
  },
  internal_error: {
    title: 'Unexpected server error',
    possibleReason: 'The backend encountered an unhandled failure while processing the request.',
    nextAction: 'Retry the action. If it keeps failing, check backend logs for details.',
  },
  unknown_error: {
    title: 'Something went wrong',
    possibleReason: 'An unexpected error occurred in the desktop client or API.',
    nextAction: 'Retry the action or reload the workspace.',
  },
}

function isRetryable(code: string): boolean {
  return RETRYABLE_CODES.has(code)
}

function fromRecovery(
  code: string,
  message: string,
  recovery: ApiRecoveryInfo,
  details?: Record<string, unknown>,
): UserFacingError {
  const affectedParameter =
    recovery.affected_parameter ||
    (typeof details?.parameter === 'string' ? details.parameter : undefined)
  const affectedTaskId =
    recovery.affected_task ||
    (typeof details?.task_id === 'string' ? details.task_id : undefined)

  return {
    code,
    title: recovery.title,
    whatHappened: recovery.what_happened || message,
    possibleReason: recovery.possible_reason,
    nextAction: recovery.next_action,
    retryable: isRetryable(code),
    affectedParameter: affectedParameter || undefined,
    affectedTaskId: affectedTaskId || undefined,
    technicalMessage: message,
  }
}

export function fromApiErrorBody(body: ApiErrorBody): UserFacingError {
  if (body.recovery) {
    return fromRecovery(body.code, body.message, body.recovery, body.details)
  }

  const guidance = CLIENT_GUIDANCE[body.code] ?? CLIENT_GUIDANCE.unknown_error
  const affectedParameter =
    typeof body.details?.parameter === 'string' ? body.details.parameter : undefined

  return {
    code: body.code,
    title: guidance.title,
    whatHappened: body.message,
    possibleReason: guidance.possibleReason,
    nextAction:
      body.code === 'invalid_input' && affectedParameter
        ? `Update "${affectedParameter}" and submit again.`
        : guidance.nextAction,
    retryable: isRetryable(body.code),
    affectedParameter,
    affectedTaskId: typeof body.details?.task_id === 'string' ? body.details.task_id : undefined,
    technicalMessage: body.message,
  }
}

export function backendUnavailableError(message?: string): UserFacingError {
  return fromApiErrorBody({
    code: 'backend_unavailable',
    message: message ?? 'The engineering backend process is not available.',
  })
}

export function apiUnreachableError(message: string): UserFacingError {
  return fromApiErrorBody({
    code: 'api_unreachable',
    message,
  })
}

export function toUserFacingError(error: unknown): UserFacingError {
  if (isApiError(error)) {
    return fromApiErrorBody({
      code: error.code,
      message: error.message,
      details: error.details,
      recovery: error.recovery,
    })
  }

  if (error instanceof Error) {
    if (error.name === 'TimeoutError' || error.message.toLowerCase().includes('timeout')) {
      return apiUnreachableError(error.message)
    }
    if (error.name === 'TypeError' && error.message.toLowerCase().includes('fetch')) {
      return apiUnreachableError('Network request failed. The backend may be offline.')
    }
    return fromApiErrorBody({
      code: 'unknown_error',
      message: error.message,
    })
  }

  return fromApiErrorBody({
    code: 'unknown_error',
    message: 'An unexpected error occurred.',
  })
}

export function toUserMessage(error: unknown): string {
  return toUserFacingError(error).whatHappened
}
