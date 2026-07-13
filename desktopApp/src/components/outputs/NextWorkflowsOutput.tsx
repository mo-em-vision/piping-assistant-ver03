import { useTaskStore } from '@/store/taskStore'

import type { NextWorkflowsOutputBlock } from '@/types/backend/outputs'

import './NextWorkflowsOutput.css'

interface NextWorkflowsOutputProps {
  block: NextWorkflowsOutputBlock
}

const RELATED_WORKFLOW_LABEL = 'Related Workflows'

export function NextWorkflowsOutput({ block }: NextWorkflowsOutputProps) {
  const createTask = useTaskStore((state) => state.createTask)
  const label = block.related_workflow_label?.trim() || RELATED_WORKFLOW_LABEL

  return (
    <article className="output-block output-next-workflows">
      <ul className="output-next-workflows__list">
        {block.suggestions.map((suggestion) => {
          const line = `${label}: ${suggestion.title}`
          return (
            <li key={suggestion.workflow_id} className="output-next-workflows__item">
              {suggestion.action?.type === 'start_workflow' ? (
                <button
                  type="button"
                  className="output-next-workflows__line-button"
                  onClick={() => void createTask(suggestion.action!.workflow_id)}
                >
                  {line}
                </button>
              ) : (
                <span className="output-next-workflows__line">{line}</span>
              )}
            </li>
          )
        })}
      </ul>
    </article>
  )
}
