import { useEffect, useRef } from 'react'

import './SidePanelContextMenu.css'

export interface SidePanelContextMenuItem {
  label: string
  onClick: () => void
  danger?: boolean
}

interface SidePanelContextMenuProps {
  x: number
  y: number
  items: SidePanelContextMenuItem[]
  ariaLabel: string
  onClose: () => void
}

export function SidePanelContextMenu({
  x,
  y,
  items,
  ariaLabel,
  onClose,
}: SidePanelContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current?.contains(event.target as Node)) {
        return
      }
      onClose()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    const handleScroll = () => {
      onClose()
    }

    window.addEventListener('mousedown', handlePointerDown)
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('scroll', handleScroll, true)

    return () => {
      window.removeEventListener('mousedown', handlePointerDown)
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [onClose])

  return (
    <div
      ref={menuRef}
      className="side-panel-context-menu"
      style={{ top: y, left: x }}
      role="menu"
      aria-label={ariaLabel}
    >
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          className={`side-panel-context-menu__item${item.danger ? ' side-panel-context-menu__item--danger' : ''}`}
          role="menuitem"
          onClick={() => {
            item.onClick()
            onClose()
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}
