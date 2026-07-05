export interface GraphTaskQueryOptions {
  taskId?: string | null
  sessionId?: string | null
  params?: Record<string, string>
}

export function readTaskIdFromUrl(): string | null {
  const taskId = new URLSearchParams(window.location.search).get('task')
  return taskId?.trim() ? taskId.trim() : null
}

export function readSessionIdFromUrl(): string | null {
  const sessionId = new URLSearchParams(window.location.search).get('session_id')
  return sessionId?.trim() ? sessionId.trim() : null
}

export function resolveTaskId(taskId?: string | null): string | null {
  const explicit = taskId?.trim()
  if (explicit) {
    return explicit
  }
  return readTaskIdFromUrl()
}

export function resolveSessionId(sessionId?: string | null): string | null {
  const explicit = sessionId?.trim()
  if (explicit) {
    return explicit
  }
  return readSessionIdFromUrl()
}

export function withTaskQuery(options: GraphTaskQueryOptions = {}): string {
  const taskId = resolveTaskId(options.taskId)
  const sessionId = resolveSessionId(options.sessionId)
  const search = new URLSearchParams(options.params ?? {})
  if (taskId) {
    search.set('task', taskId)
  }
  if (sessionId) {
    search.set('session_id', sessionId)
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}
