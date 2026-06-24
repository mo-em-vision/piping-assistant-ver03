export function confirmTaskDeletion(taskName: string): boolean {
  return window.confirm(
    `Delete "${taskName}"?\n\nThis will permanently remove the task and its saved inputs. This cannot be undone.`,
  )
}
