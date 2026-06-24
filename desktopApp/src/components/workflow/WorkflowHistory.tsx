import { useDeferredValue, useEffect, useRef } from 'react'

import { OutputRenderer } from '@/components/outputs/OutputRenderer'

import type { WorkflowHistoryItem } from './buildWorkflowHistory'

import './WorkflowPanel.css'

interface WorkflowHistoryProps {
  items: WorkflowHistoryItem[]
  emptyMessage?: string
}

function WorkflowHistoryMessage({ item }: { item: WorkflowHistoryItem }) {
  if (item.kind === 'report-statement') {
    return <p className="workflow-report__paragraph">{item.body}</p>
  }

  if (item.kind === 'node-content') {
    return (
      <article className="workflow-message workflow-message--node-content">
        <div className="workflow-message__content">
          <OutputRenderer blocks={[item.block]} emptyMessage="" variant="inline" />
        </div>
      </article>
    )
  }

  return (
    <article className="workflow-message workflow-message--output">
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
  const deferredItems = useDeferredValue(items)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [deferredItems])

  return (
    <div className="workflow-panel__history" aria-live="polite">
      {deferredItems.length === 0 ? (
        <p className="workflow-panel__empty">{emptyMessage}</p>
      ) : (
        deferredItems.map((item) => <WorkflowHistoryMessage key={item.id} item={item} />)
      )}
      <div ref={endRef} />
    </div>
  )
}
