import { useEffect } from 'react'

import { useUiStore } from '@/store/uiStore'

export function useWindowDisplayState() {
  const setFullScreen = useUiStore((state) => state.setFullScreen)

  useEffect(() => {
    const api = window.electronAPI
    if (!api?.getWindowDisplayState) {
      return
    }

    void api.getWindowDisplayState().then((state) => {
      setFullScreen(state.isFullScreen)
    })

    return api.onWindowDisplayStateChange((state) => {
      setFullScreen(state.isFullScreen)
    })
  }, [setFullScreen])
}
