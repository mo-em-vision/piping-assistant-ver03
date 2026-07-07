import { useEffect } from 'react'

import { env } from '@/config/env'
import { useDevUiActive } from '@/hooks/useDevUiActive'
import { useRightPanelStore } from '@/store/rightPanelStore'
import { useTaskStore } from '@/store/taskStore'

export function DevPanelTabsSync() {
  const devModeActive = useDevUiActive()
  const activeTask = useTaskStore((state) => state.activeTask)
  const syncDevTabs = useRightPanelStore((state) => state.syncDevTabs)

  useEffect(() => {
    if (!env.devToolsAvailable) {
      return
    }
    syncDevTabs(devModeActive, Boolean(activeTask))
  }, [devModeActive, activeTask, syncDevTabs])

  return null
}
