import { useCallback, useRef } from 'react'

import './ResizeHandle.css'

interface ResizeHandleProps {
  onResizeDelta: (delta: number) => void
}

export function ResizeHandle({ onResizeDelta }: ResizeHandleProps) {
  const lastX = useRef<number | null>(null)

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      lastX.current = event.clientX
      event.currentTarget.setPointerCapture(event.pointerId)

      const handlePointerMove = (moveEvent: PointerEvent) => {
        if (lastX.current === null) {
          return
        }
        const delta = moveEvent.clientX - lastX.current
        lastX.current = moveEvent.clientX
        onResizeDelta(delta)
      }

      const handlePointerUp = () => {
        lastX.current = null
        window.removeEventListener('pointermove', handlePointerMove)
        window.removeEventListener('pointerup', handlePointerUp)
      }

      window.addEventListener('pointermove', handlePointerMove)
      window.addEventListener('pointerup', handlePointerUp)
    },
    [onResizeDelta],
  )

  return (
    <div
      className="resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      onPointerDown={handlePointerDown}
    />
  )
}
