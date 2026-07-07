import { useInspectorStore } from './inspectorStore'

import type { ExecutionTraceStepDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type ExecutionTracePanelProps = {
  steps: ExecutionTraceStepDto[]
}

export function ExecutionTracePanel({ steps }: ExecutionTracePanelProps) {
  const selectedStepIndex = useInspectorStore((state) => state.selectedStepIndex)
  const selectStep = useInspectorStore((state) => state.selectStep)
  const selectNode = useInspectorStore((state) => state.selectNode)

  if (!steps.length) {
    return <p className="inspector-empty">No steps yet — workflow has not executed nodes.</p>
  }

  return (
    <ol className="inspector-trace-list inspector-trace-list--compact">
      {steps.map((step) => {
        const selected = selectedStepIndex === step.step_index
        return (
          <li key={`${step.step_index}-${step.node_id}`}>
            <button
              type="button"
              className={`inspector-trace-step inspector-trace-step--compact${selected ? ' inspector-trace-step--selected' : ''}`}
              onClick={() => {
                selectStep(step.step_index)
                selectNode(step.node_id)
              }}
            >
              <span className="inspector-trace-step__index">{step.step_index + 1}</span>
              <span className={`inspector-status inspector-status--${step.status}`}>{step.status}</span>
              <span className="inspector-trace-step__node">{step.node_id}</span>
              <span className="inspector-trace-step__reason">{step.selection_reason}</span>
              {step.errors?.length ? (
                <span className="inspector-trace-step__error">{step.errors.join('; ')}</span>
              ) : null}
            </button>
          </li>
        )
      })}
    </ol>
  )
}
