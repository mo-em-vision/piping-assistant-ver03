import { cloneElement, isValidElement, type MouseEvent, type ReactElement, type ReactNode } from 'react'

import { useDevNodeHover } from '@/components/dev/DevNodeHoverProvider'
import { env } from '@/config/env'
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
  const resolved = resolveProvenance(provenance, fallbackProvenance)

  if (!env.devMode || !resolved || !hover) {
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

  if (isValidElement(children)) {
    const child = children as ReactElement<{ className?: string }>
    const mergedClassName = [child.props.className, 'dev-node-hover-surface--interactive', className]
      .filter(Boolean)
      .join(' ')

    return cloneElement(child, {
      className: mergedClassName,
      onMouseEnter: handleMouseEnter,
      onMouseMove: handleMouseMove,
      onMouseLeave: handleMouseLeave,
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
    >
      {children}
    </span>
  )
}
