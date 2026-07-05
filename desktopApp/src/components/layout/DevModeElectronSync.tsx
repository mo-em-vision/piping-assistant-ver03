import { useEffect } from 'react'

import { env } from '@/config/env'
import { setDevUiActive } from '@dev-ui/devUiActive'
import { useDevToolsStore } from '@/store/devToolsStore'

export function DevModeElectronSync() {
  const devModeActive = useDevToolsStore((state) => state.devModeActive)

  useEffect(() => {
    const active = env.devToolsAvailable && devModeActive
    setDevUiActive(active)
    if (!env.devToolsAvailable) {
      return
    }
    void window.electronAPI?.syncDevMode?.(devModeActive)
  }, [devModeActive])

  return null
}
