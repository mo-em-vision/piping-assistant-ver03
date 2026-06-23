import type { ReactNode } from 'react'

import './PanelSection.css'

interface PanelSectionProps {
  title: string
  action?: ReactNode
  className?: string
  children: ReactNode
}

export function PanelSection({ title, action, className, children }: PanelSectionProps) {
  return (
    <section className={className ? `panel-section ${className}` : 'panel-section'}>
      <header className="panel-section__header">
        <h3 className="panel-section__title">{title}</h3>
        {action}
      </header>
      <div className="panel-section__body">{children}</div>
    </section>
  )
}
