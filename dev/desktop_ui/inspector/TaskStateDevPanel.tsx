import { useMemo } from 'react'

import type { InspectionPayloadDto, TaskStateViewsDto } from '@/types/backend/inspection'
import type { TaskStateDto } from '@/types/backend/api'

import { DecisionsPanel } from './DecisionsPanel'
import { FactsTable } from './FactsTable'
import { InspectorAdvancedSection } from './InspectorAdvancedSection'
import { InspectorDebugNotice } from './InspectorDebugNotice'
import { InspectorDisclosureSection } from './InspectorDisclosureSection'
import { OutputsPanel } from './OutputsPanel'
import { TaskStateHeaderCard } from './TaskStateHeaderCard'
import { TraceTimelinePanel } from './TraceTimelinePanel'
import { ValidationPanel } from './ValidationPanel'

import './InspectorPanels.css'

type TaskStateDevPanelProps = {
  payload: InspectionPayloadDto
  activeTaskState: TaskStateDto | null
}

function resolveTaskStateViews(
  payload: InspectionPayloadDto,
): TaskStateViewsDto | null {
  if (payload.task_state_views) {
    return payload.task_state_views
  }
  return null
}

export function TaskStateDevPanel({ payload, activeTaskState }: TaskStateDevPanelProps) {
  const views = useMemo(() => resolveTaskStateViews(payload), [payload])

  if (!views) {
    return (
      <p className="inspector-empty">
        Task state views require DEV_INSPECTION_ENABLED=1 on the backend.
      </p>
    )
  }

  const factsSummary = `${views.facts_view.length} values · ${views.state_summary.missing_input_count} missing`
  const decisionsSummary = `${views.decisions_view.length} decisions / assumptions`
  const outputsSummary = `${views.outputs_view.length} outputs`
  const timelineSummary = `${views.trace_timeline.length} events`
  const validationOpen = views.validation_view.status !== 'ok'

  return (
    <div className="inspector-task-state inspector-task-state--structured">
      <InspectorDebugNotice />
      <TaskStateHeaderCard summary={views.state_summary} />

      <InspectorDisclosureSection title="Facts / inputs" summary={factsSummary} defaultOpen>
        <FactsTable rows={views.facts_view} />
      </InspectorDisclosureSection>

      {views.decisions_view.length ? (
        <InspectorDisclosureSection title="Decisions and assumptions" summary={decisionsSummary}>
          <DecisionsPanel rows={views.decisions_view} />
        </InspectorDisclosureSection>
      ) : null}

      <InspectorDisclosureSection title="Outputs produced" summary={outputsSummary}>
        <OutputsPanel rows={views.outputs_view} />
      </InspectorDisclosureSection>

      <InspectorDisclosureSection
        title="Validation and warnings"
        summary={views.validation_view.status}
        defaultOpen={validationOpen}
      >
        <ValidationPanel view={views.validation_view} />
      </InspectorDisclosureSection>

      <InspectorDisclosureSection title="Event timeline" summary={timelineSummary}>
        <TraceTimelinePanel rows={views.trace_timeline} />
      </InspectorDisclosureSection>

      <InspectorAdvancedSection title="Advanced / Raw Data — Canonical task state" data={payload.canonical_task_state} />
      <InspectorAdvancedSection title="Full inspection payload" data={payload} />
      {activeTaskState ? (
        <InspectorAdvancedSection title="Active task state (raw)" data={activeTaskState} />
      ) : null}
    </div>
  )
}
