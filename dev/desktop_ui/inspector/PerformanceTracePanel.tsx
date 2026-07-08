import { useMemo } from 'react'

import type { PerformanceSpanDto, PerformanceTraceDto } from '@/types/backend/inspection'

import { InspectorAdvancedSection } from './InspectorAdvancedSection'
import {
  durationSeverity,
  formatDurationMs,
  isInspectionPollTrace,
  severityClassName,
  sortedSpans,
  spanDepth,
  triggerLabel,
} from './performanceTraceHelpers'
import { usePerformanceTraces } from './usePerformanceTraces'

import './InspectorPanels.css'

function OpTypeBadge({ opType }: { opType: string }) {
  return <span className="perf-trace-row__op-type">{opType}</span>
}

function SpanRow({
  span,
  spanById,
}: {
  span: PerformanceSpanDto
  spanById: Map<string, PerformanceSpanDto>
}) {
  const severity = durationSeverity(span.duration_ms)
  const depth = spanDepth(span, spanById)

  return (
    <tr className={`perf-trace-row ${severityClassName(severity)}`}>
      <td className="perf-trace-row__name" style={{ paddingLeft: `${depth * 12 + 8}px` }}>
        {span.name}
      </td>
      <td className="perf-trace-row__duration">{formatDurationMs(span.duration_ms)}</td>
      <td>
        <OpTypeBadge opType={span.op_type} />
      </td>
      <td className="perf-trace-row__status">{span.status}</td>
      <td className="perf-trace-row__llm">{span.llm ? 'yes' : '—'}</td>
      <td className="perf-trace-row__notes">{span.notes ?? '—'}</td>
    </tr>
  )
}

function TraceSummary({ trace }: { trace: PerformanceTraceDto }) {
  const severity = durationSeverity(trace.total_duration_ms)
  const pollTrace = isInspectionPollTrace(trace.trigger)

  return (
    <div className="perf-trace-summary">
      <div className="perf-trace-summary__row">
        <span className="perf-trace-summary__label">Trace</span>
        <code className="perf-trace-summary__trace-id">{trace.trace_id}</code>
      </div>
      <div className="perf-trace-summary__row">
        <span className="perf-trace-summary__label">Trigger</span>
        <span
          className={`perf-trace-summary__trigger${pollTrace ? ' perf-trace-summary__trigger--poll' : ''}`}
          title={trace.trigger}
        >
          {triggerLabel(trace.trigger)}
        </span>
      </div>
      <div className="perf-trace-summary__row">
        <span className="perf-trace-summary__label">Total</span>
        <span className={`perf-trace-summary__duration ${severityClassName(severity)}`}>
          {formatDurationMs(trace.total_duration_ms)}
        </span>
      </div>
      <div className="perf-trace-summary__row">
        <span className="perf-trace-summary__label">Status</span>
        <span>{trace.status}</span>
      </div>
      {trace.llm_call_occurred ? (
        <div className="perf-trace-summary__badge perf-trace-summary__badge--llm">LLM call</div>
      ) : null}
      {trace.spans_omitted > 0 ? (
        <div className="perf-trace-summary__note">
          {trace.spans_omitted} span(s) omitted; see spans_truncated in table.
        </div>
      ) : null}
      {trace.error ? <div className="perf-trace-summary__error">{trace.error}</div> : null}
    </div>
  )
}

export function PerformanceTracePanel() {
  const { traces, selectedTrace, selectedTraceId, setSelectedTraceId, error, loading } =
    usePerformanceTraces()

  const spanById = useMemo(() => {
    const map = new Map<string, PerformanceSpanDto>()
    for (const span of selectedTrace?.spans ?? []) {
      map.set(span.span_id, span)
    }
    return map
  }, [selectedTrace?.spans])

  const spanRows = useMemo(
    () => sortedSpans(selectedTrace?.spans ?? []),
    [selectedTrace?.spans],
  )

  return (
    <div className="inspector-performance-trace">
      <div className="inspector-performance-trace__header">
        <h3 className="inspector-workflow-status__title">Performance Trace</h3>
        {loading ? <span className="inspector-performance-trace__status">Refreshing…</span> : null}
      </div>

      {error ? <p className="inspector-empty inspector-performance-trace__error">{error}</p> : null}

      {!error && traces.length === 0 ? (
        <p className="inspector-empty inspector-performance-trace__idle">
          Submit a workflow input to record a performance trace.
        </p>
      ) : null}

      {!error && traces.length > 0 && selectedTrace ? (
        <>
          <label className="perf-trace-selector">
            <span className="perf-trace-selector__label">Recent trace</span>
            <select
              className="perf-trace-selector__select"
              value={selectedTraceId ?? selectedTrace.trace_id}
              onChange={(event) => setSelectedTraceId(event.target.value)}
            >
              {traces.map((trace) => (
                <option key={trace.trace_id} value={trace.trace_id}>
                  {triggerLabel(trace.trigger)} — {formatDurationMs(trace.total_duration_ms)} —{' '}
                  {trace.trace_id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>

          <TraceSummary trace={selectedTrace} />

          {isInspectionPollTrace(selectedTrace.trigger) ? (
            <p className="perf-trace-summary__poll-note">
              This trace is from inspection polling and is separate from submit_input workflow
              steps.
            </p>
          ) : null}

          <div className="perf-trace-table-wrap">
            <table className="perf-trace-table">
              <thead>
                <tr>
                  <th>Operation</th>
                  <th>Duration</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>LLM</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {spanRows.map((span) => (
                  <SpanRow key={span.span_id} span={span} spanById={spanById} />
                ))}
              </tbody>
            </table>
          </div>

          <InspectorAdvancedSection title="Advanced JSON" data={selectedTrace} />
        </>
      ) : null}
    </div>
  )
}
