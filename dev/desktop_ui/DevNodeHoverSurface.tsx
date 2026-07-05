import { cloneElement, isValidElement, useSyncExternalStore, type MouseEvent, type ReactElement, type ReactNode } from 'react'

import { useDevNodeHover } from '@dev-ui/DevNodeHoverProvider'
import { getDevUiActive, subscribeDevUiActive } from '@dev-ui/devUiActive'
import type { NodeProvenanceDto } from '@/types/backend/api'
import { resolveProvenance } from '@/utils/nodeProvenance'

import './DevNodeHover.css'

interface DevNodeHoverSurfaceProps {
  provenance?: NodeProvenanceDto | null
  fallbackProvenance?: NodeProvenanceDto | null
  children: ReactNode
  className?: string
}

export function DevNodeHoverSurface({
  provenance,
  fallbackProvenance,
  children,
  className,
}: DevNodeHoverSurfaceProps) {
  const hover = useDevNodeHover()
  const devUiActive = useSyncExternalStore(subscribeDevUiActive, getDevUiActive, () => false)
  const resolved = resolveProvenance(provenance, fallbackProvenance)

  if (!devUiActive || !resolved || !hover) {
    return <>{children}</>
  }

  const handleMouseEnter = (event: MouseEvent<HTMLElement>) => {
    hover.showHover(resolved, event.clientX, event.clientY)
  }

  const handleMouseMove = (event: MouseEvent<HTMLElement>) => {
    hover.showHover(resolved, event.clientX, event.clientY)
  }

  const handleMouseLeave = () => {
    hover.hideHover()
  }

  const handleClick = (event: MouseEvent<HTMLElement>) => {
    const target = event.target as HTMLElement
    if (target.closest('a, button, input, textarea, select, [role="button"]')) {
      return
    }
    hover.openNodeEdit(resolved)
  }

  if (isValidElement(children)) {
    const child = children as ReactElement<{
      className?: string
      onClick?: (event: MouseEvent<HTMLElement>) => void
    }>
    const mergedClassName = [child.props.className, 'dev-node-hover-surface--interactive', className]
      .filter(Boolean)
      .join(' ')

    return cloneElement(child, {
      className: mergedClassName,
      onMouseEnter: handleMouseEnter,
      onMouseMove: handleMouseMove,
      onMouseLeave: handleMouseLeave,
      onClick: (event: MouseEvent<HTMLElement>) => {
        child.props.onClick?.(event)
        if (!event.defaultPrevented) {
          handleClick(event)
        }
      },
    })
  }

  return (
    <span
      className={['dev-node-hover-surface', 'dev-node-hover-surface--interactive', className]
        .filter(Boolean)
        .join(' ')}
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      {children}
    </span>
  )
}
