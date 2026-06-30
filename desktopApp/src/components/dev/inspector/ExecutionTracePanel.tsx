import { useInspectorStore } from './inspectorStore'

import type { ExecutionTraceStepDto } from '@/types/backend/inspection'

import './InspectorPanels.css'

type ExecutionTracePanelProps = {
  steps: ExecutionTraceStepDto[]
}

function formatIo(record: Record<string, unknown>): string {
  const entries = Object.entries(record)
  if (!entries.length) {
    return '—'
  }
  return entries
    .slice(0, 6)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(', ')
}

export function ExecutionTracePanel({ steps }: ExecutionTracePanelProps) {
  const selectedStepIndex = useInspectorStore((state) => state.selectedStepIndex)
  const selectStep = useInspectorStore((state) => state.selectStep)
  const selectNode = useInspectorStore((state) => state.selectNode)

  if (!steps.length) {
    return <p className="inspector-empty">No execution steps recorded yet.</p>
  }

  return (
    <ol className="inspector-trace-list">
      {steps.map((step) => {
        const selected = selectedStepIndex === step.step_index
        return (
          <li key={`${step.step_index}-${step.node_id}`}>
            <button
              type="button"
              className={`inspector-trace-step${selected ? ' inspector-trace-step--selected' : ''}`}
              onClick={() => {
                selectStep(step.step_index)
                selectNode(step.node_id)
              }}
            >
              <div className="inspector-trace-step__header">
                <span className="inspector-trace-step__index">Step {step.step_index + 1}</span>
                <span className={`inspector-status inspector-status--${step.status}`}>{step.status}</span>
                {step.duration_ms != null ? (
                  <span className="inspector-trace-step__duration">{step.duration_ms.toFixed(1)} ms</span>
                ) : null}
              </div>
              <div className="inspector-trace-step__node">{step.node_id}</div>
              <div className="inspector-trace-step__meta">
                <span>{step.node_type || 'node'}</span>
                <span>{step.selection_reason}</span>
              </div>
              <div className="inspector-trace-step__io">
                <div>
                  <strong>Inputs:</strong> {formatIo(step.inputs)}
                </div>
                <div>
                  <strong>Outputs:</strong> {formatIo(step.outputs)}
                </div>
              </div>
              {step.errors?.length ? (
                <div className="inspector-trace-step__error">{step.errors.join('; ')}</div>
              ) : null}
            </button>
          </li>
        )
      })}
    </ol>
  )
}
