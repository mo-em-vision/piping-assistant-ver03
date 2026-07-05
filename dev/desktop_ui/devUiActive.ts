let devUiActive = false
const listeners = new Set<() => void>()

export function setDevUiActive(active: boolean): void {
  devUiActive = active
  for (const listener of listeners) {
    listener()
  }
}

export function getDevUiActive(): boolean {
  return devUiActive
}

export function subscribeDevUiActive(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
