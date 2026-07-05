import { inspectionApi } from '@/services/api/inspectionApi'

import type { IntegrityCheckDto, InspectionPayloadDto, ReplayFrameDto } from '@/types/backend/inspection'

import { useInspectorStore } from './inspectorStore'

import './InspectorPanels.css'

type ReplayPanelProps = {
  frames: ReplayFrameDto[]
  taskId: string | null
  sessionId: string | null
}

export function ReplayPanel({ frames, taskId, sessionId }: ReplayPanelProps) {
  const replayFrameIndex = useInspectorStore((state) => state.replayFrameIndex)
  const setReplayFrameIndex = useInspectorStore((state) => state.setReplayFrameIndex)
  const selectNode = useInspectorStore((state) => state.selectNode)

  const frame = frames[replayFrameIndex]
  const maxIndex = Math.max(frames.length - 1, 0)

  const setBreakpoint = async (payload: { paused?: boolean; step?: boolean }) => {
    if (!taskId) {
      return
    }
    await inspectionApi.setBreakpoint(taskId, payload, sessionId ?? undefined)
  }

  return (
    <div className="inspector-replay">
      <div className="inspector-replay__controls">
        <button type="button" disabled={!frames.length} onClick={() => setReplayFrameIndex(0)}>
          ⏮
        </button>
        <button
          type="button"
          disabled={replayFrameIndex <= 0}
          onClick={() => setReplayFrameIndex(Math.max(0, replayFrameIndex - 1))}
        >
          ◀
        </button>
        <button type="button" onClick={() => void setBreakpoint({ paused: true })}>
          Pause live
        </button>
        <button type="button" onClick={() => void setBreakpoint({ step: true })}>
          Step live
        </button>
        <button type="button" onClick={() => void setBreakpoint({ paused: false })}>
          Resume live
        </button>
        <button
          type="button"
          disabled={replayFrameIndex >= maxIndex}
          onClick={() => setReplayFrameIndex(Math.min(maxIndex, replayFrameIndex + 1))}
        >
          ▶
        </button>
        <button type="button" disabled={!frames.length} onClick={() => setReplayFrameIndex(maxIndex)}>
          ⏭
        </button>
        <span>
          Frame {frames.length ? replayFrameIndex + 1 : 0} / {frames.length}
        </span>
      </div>
      {frame ? (
        <div className="inspector-replay__frame">
          <p>
            <strong>Active node:</strong> {frame.active_node ?? '—'}
          </p>
          <p>
            <strong>Visited:</strong> {frame.visited_nodes.join(', ') || '—'}
          </p>
          <p>
            <strong>Pending:</strong> {frame.pending_nodes.join(', ') || '—'}
          </p>
          <button type="button" onClick={() => frame.active_node && selectNode(frame.active_node)}>
            Focus active node
          </button>
          <pre className="inspector-code">{JSON.stringify(frame.context, null, 2)}</pre>
        </div>
      ) : (
        <p className="inspector-empty">No replay frames available.</p>
      )}
    </div>
  )
}

type IntegrityTestsPanelProps = {
  checks: IntegrityCheckDto[]
  taskId: string | null
  sessionId: string | null
  onRefresh: () => void
}

export function IntegrityTestsPanel({ checks, taskId, sessionId, onRefresh }: IntegrityTestsPanelProps) {
  const runChecks = async () => {
    if (!taskId) {
      return
    }
    await inspectionApi.runIntegrity(taskId, sessionId ?? undefined)
    onRefresh()
  }

  return (
    <div className="inspector-integrity">
      <button type="button" onClick={() => void runChecks()}>
        Run checks
      </button>
      <ul>
        {checks.map((check) => (
          <li key={check.check_id} className={check.passed ? 'inspector-integrity--pass' : 'inspector-integrity--fail'}>
            <strong>{check.name}</strong>: {check.message}
          </li>
        ))}
      </ul>
    </div>
  )
}

type ContextPanelProps = {
  workflowState: Record<string, unknown>
  selectedNodeId: string | null
}

export function ContextPanel({ workflowState, selectedNodeId }: ContextPanelProps) {
  const currentNode = workflowState.current_node
  const nodeDocs = workflowState.node_documentation as Record<string, Record<string, unknown>> | undefined
  const doc = selectedNodeId && nodeDocs ? nodeDocs[selectedNodeId] : null

  return (
    <div className="inspector-context">
      <p>
        <strong>Current node:</strong> {String(currentNode ?? '—')}
      </p>
      {doc ? <pre className="inspector-code">{JSON.stringify(doc, null, 2)}</pre> : null}
    </div>
  )
}

type VariablesPanelProps = {
  workflowState: Record<string, unknown>
}

export function VariablesPanel({ workflowState }: VariablesPanelProps) {
  return (
    <pre className="inspector-code">
      {JSON.stringify(
        {
          parameters: workflowState.parameters,
          variable_values: workflowState.variable_values,
        },
        null,
        2,
      )}
    </pre>
  )
}

type LogsPanelProps = {
  executionEvents: Array<Record<string, unknown>>
  lifecycleEvents: Array<Record<string, unknown>>
}

export function LogsPanel({ executionEvents, lifecycleEvents }: LogsPanelProps) {
  return (
    <div className="inspector-logs">
      <h4>Execution events</h4>
      <pre className="inspector-code">{JSON.stringify(executionEvents, null, 2)}</pre>
      <h4>Lifecycle events</h4>
      <pre className="inspector-code">{JSON.stringify(lifecycleEvents, null, 2)}</pre>
    </div>
  )
}

type PerformancePanelProps = {
  performance: InspectionPayloadDto['performance']
}

export function PerformancePanel({ performance }: PerformancePanelProps) {
  return (
    <div className="inspector-performance">
      <p>
        <strong>Total:</strong> {performance.total_duration_ms.toFixed(1)} ms across {performance.step_count} steps
      </p>
      <ul>
        {Object.entries(performance.by_node_ms).map(([nodeId, ms]) => (
          <li key={nodeId}>
            {nodeId}: {ms.toFixed(1)} ms
          </li>
        ))}
      </ul>
    </div>
  )
}
