import { useEffect } from 'react'

import { env } from '@/config/env'
import { useDevToolsStore } from '@/store/devToolsStore'

export function DevModeElectronSync() {
  const devModeActive = useDevToolsStore((state) => state.devModeActive)

  useEffect(() => {
    if (!env.devToolsAvailable) {
      return
    }
    void window.electronAPI?.syncDevMode?.(devModeActive)
  }, [devModeActive])

  return null
}
