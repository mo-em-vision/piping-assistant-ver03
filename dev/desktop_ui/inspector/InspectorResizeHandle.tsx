import { useCallback, useRef, type PointerEvent } from 'react'

import { useInspectorStore } from './inspectorStore'

export function InspectorResizeHandle() {
  const setHeight = useInspectorStore((state) => state.setHeight)
  const lastY = useRef<number | null>(null)

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      lastY.current = event.clientY
      event.currentTarget.setPointerCapture(event.pointerId)

      const handlePointerMove = (moveEvent: PointerEvent) => {
        if (lastY.current === null) {
          return
        }
        const delta = lastY.current - moveEvent.clientY
        lastY.current = moveEvent.clientY
        setHeight(useInspectorStore.getState().height + delta)
      }

      const handlePointerUp = () => {
        lastY.current = null
        window.removeEventListener('pointermove', handlePointerMove)
        window.removeEventListener('pointerup', handlePointerUp)
      }

      window.addEventListener('pointermove', handlePointerMove)
      window.addEventListener('pointerup', handlePointerUp)
    },
    [setHeight],
  )

  return (
    <div
      className="developer-inspector__resize-handle"
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize inspector"
      onPointerDown={handlePointerDown}
    />
  )
}
