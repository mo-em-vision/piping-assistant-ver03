import { env } from '@/config/env'
import { useDevToolsStore } from '@/store/devToolsStore'

export function useDevUiActive(): boolean {
  const devModeActive = useDevToolsStore((state) => state.devModeActive)
  return env.devToolsAvailable && devModeActive
}
