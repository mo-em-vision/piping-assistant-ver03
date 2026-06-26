export function confirmProjectDeletion(projectName: string): boolean {
  return window.confirm(
    `Delete project "${projectName}"?\n\nThis will permanently remove the project and all tasks inside it. This cannot be undone.`,
  )
}
