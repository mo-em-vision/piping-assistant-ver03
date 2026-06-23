import { useEffect, useRef } from 'react'

import { OutputRenderer } from '@/components/outputs/OutputRenderer'

import type { WorkflowHistoryItem } from './buildWorkflowHistory'

import './WorkflowPanel.css'

interface WorkflowHistoryProps {
  items: WorkflowHistoryItem[]
  emptyMessage?: string
}

function WorkflowHistoryMessage({ item }: { item: WorkflowHistoryItem }) {
  if (item.kind === 'prompt') {
    return (
      <article className={`workflow-message workflow-message--assistant workflow-message--${item.stepStatus}`}>
        <div className="workflow-message__meta">Workflow</div>
        <div className="workflow-message__bubble">
          <p className="workflow-message__title">{item.title}</p>
          {item.body ? <p className="workflow-message__body">{item.body}</p> : null}
        </div>
      </article>
    )
  }

  if (item.kind === 'user-input') {
    return (
      <article className="workflow-message workflow-message--user">
        <div className="workflow-message__meta">{item.label}</div>
        <div className="workflow-message__bubble">{item.value}</div>
      </article>
    )
  }

  return (
    <article className="workflow-message workflow-message--output">
      <div className="workflow-message__meta">Output</div>
      <div className="workflow-message__content">
        <OutputRenderer blocks={[item.block]} emptyMessage="" variant="inline" />
      </div>
    </article>
  )
}

export function WorkflowHistory({
  items,
  emptyMessage = 'Workflow history will appear here as you progress.',
}: WorkflowHistoryProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  return (
    <div className="workflow-panel__history" aria-live="polite">
      {items.length === 0 ? (
        <p className="workflow-panel__empty">{emptyMessage}</p>
      ) : (
        items.map((item) => <WorkflowHistoryMessage key={item.id} item={item} />)
      )}
      <div ref={endRef} />
    </div>
  )
}
