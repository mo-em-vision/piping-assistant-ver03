import type { UserFacingError } from '@/types/frontend/userError'

export const retryableApiError: UserFacingError = {
  code: 'api_unreachable',
  title: 'Cannot reach API',
  whatHappened: 'Network request failed.',
  possibleReason: 'The desktop app could not complete a health check against the backend.',
  nextAction: 'Retry after confirming the Python API process is running.',
  retryable: true,
}

export const invalidInputError: UserFacingError = {
  code: 'invalid_input',
  title: 'Invalid engineering input',
  whatHappened: 'design_pressure must be positive',
  possibleReason: 'The submitted value failed validation or is outside allowed limits.',
  nextAction: 'Update "design_pressure" and submit again.',
  retryable: false,
  affectedParameter: 'design_pressure',
}
