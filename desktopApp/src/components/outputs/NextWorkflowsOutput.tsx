import { useTaskStore } from '@/store/taskStore'

import type { NextWorkflowsOutputBlock } from '@/types/backend/outputs'

import './NextWorkflowsOutput.css'

interface NextWorkflowsOutputProps {
  block: NextWorkflowsOutputBlock
}

export function NextWorkflowsOutput({ block }: NextWorkflowsOutputProps) {
  const createTask = useTaskStore((state) => state.createTask)

  return (
    <article className="output-block output-next-workflows">
      {block.title ? <h4 className="output-block__title">{block.title}</h4> : null}
      {block.content ? <p className="output-next-workflows__intro">{block.content}</p> : null}
      <ul className="output-next-workflows__list">
        {block.suggestions.map((suggestion) => (
          <li key={suggestion.workflow_id} className="output-next-workflows__item">
            <div className="output-next-workflows__item-body">
              <strong className="output-next-workflows__item-title">{suggestion.title}</strong>
              {suggestion.description ? (
                <p className="output-next-workflows__item-description">{suggestion.description}</p>
              ) : null}
            </div>
            {suggestion.action?.type === 'start_workflow' ? (
              <button
                type="button"
                className="output-next-workflows__start-button"
                onClick={() => void createTask(suggestion.action!.workflow_id)}
              >
                Start workflow
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </article>
  )
}
