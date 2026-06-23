const ACTIVE_PROJECT_KEY = 'desktop:activeProjectId'

export function readActiveProjectId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_PROJECT_KEY)
  } catch {
    return null
  }
}

export function writeActiveProjectId(projectId: string): void {
  try {
    localStorage.setItem(ACTIVE_PROJECT_KEY, projectId)
  } catch {
    // Ignore storage failures in restricted environments.
  }
}
