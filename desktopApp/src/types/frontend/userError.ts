export interface UserFacingError {
  code: string
  title: string
  whatHappened: string
  possibleReason: string
  nextAction: string
  retryable: boolean
  affectedParameter?: string
  affectedTaskId?: string
  technicalMessage?: string
}
