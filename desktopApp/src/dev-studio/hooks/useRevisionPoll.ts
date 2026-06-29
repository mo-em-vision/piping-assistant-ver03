import { useEffect } from 'react'

import { useDevStudioStore } from '@/dev-studio/store/devStudioStore'

export function useRevisionPoll(intervalMs = 3000) {
  const checkRevision = useDevStudioStore((s) => s.checkRevision)

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') {
        void checkRevision()
      }
    }
    const id = window.setInterval(tick, intervalMs)
    return () => window.clearInterval(id)
  }, [checkRevision, intervalMs])
}
