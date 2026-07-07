import type { EngineeringPlanDto, EngineeringPlanViewDto, PlannerTraversalStateDto } from '@/types/backend/inspection'

import { PlannerTraversalPanel } from './PlannerTraversalPanel'

import './InspectorPanels.css'

const STATUS_CLASS: Record<string, string> = {
  Complete: 'inspector-plan-status--done',
  Needed: 'inspector-plan-status--missing',
  'In progress': 'inspector-plan-status--active',
  'Waiting on dependencies': 'inspector-plan-status--blocked',
  Pending: 'inspector-plan-status--pending',
}

function statusClass(label: string | undefined): string {
  if (!label) {
    return ''
  }
  return STATUS_CLASS[label] ?? ''
}

type EngineeringPlanPanelProps = {
  plan: EngineeringPlanViewDto
}

export function EngineeringPlanPanel({ plan }: EngineeringPlanPanelProps) {
  const overview = plan.overview

  return (
    <div className="inspector-engineering-plan">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Engineering plan</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Goal</dt>
            <dd>{overview.goal}</dd>
          </div>
          <div>
            <dt>Target</dt>
            <dd>{overview.target}</dd>
          </div>
          <div>
            <dt>Phase</dt>
            <dd>{overview.current_phase ?? '—'}</dd>
          </div>
          <div>
            <dt>Progress</dt>
            <dd>
              {overview.resolved_count} complete · {overview.remaining_count} remaining
            </dd>
          </div>
          {overview.next_input ? (
            <div>
              <dt>Next input</dt>
              <dd className="inspector-status-highlight">{overview.next_input.label}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      {plan.branch_decisions?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Branch decisions</h3>
          <ul className="inspector-missing-list">
            {plan.branch_decisions.map((decision) => (
              <li key={`${decision.field}-${decision.selected_node}`}>
                <strong>{decision.field.replaceAll('_', ' ')}</strong>: {decision.value} →{' '}
                {decision.selected_node}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {plan.phases.map((phase) => (
        <section key={phase.id} className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">
            {phase.title}
            <span className={`inspector-plan-status ${statusClass(phase.status_label)}`}>
              {phase.status_label}
            </span>
          </h3>
          <ul className="inspector-plan-requirements">
            {phase.requirements.map((req) => (
              <li key={req.field} className="inspector-plan-requirement">
                <div className="inspector-plan-requirement__header">
                  <strong>{req.label}</strong>
                  <span className={`inspector-plan-status ${statusClass(req.status_label)}`}>
                    {req.status_label}
                  </span>
                </div>
                <p className="inspector-rationale-meta">
                  {req.kind}
                  {req.depends_on?.length ? ` · depends on ${req.depends_on.join(', ')}` : ''}
                </p>
                {req.alternatives?.length ? (
                  <ul className="inspector-missing-list">
                    {req.alternatives.map((alt) => (
                      <li key={alt.label}>
                        {alt.label} ({alt.method})
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {plan.calculations.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Calculations</h3>
          <ul className="inspector-plan-requirements">
            {plan.calculations.map((calc) => (
              <li key={calc.field} className="inspector-plan-requirement">
                <div className="inspector-plan-requirement__header">
                  <strong>{calc.label}</strong>
                  <span className={`inspector-plan-status ${statusClass(calc.status_label)}`}>
                    {calc.status_label}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {plan.warnings?.length ? (
        <section className="inspector-workflow-status__section">
          <h3 className="inspector-workflow-status__title">Plan warnings</h3>
          <ul className="inspector-warning-list">
            {plan.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}

export function isEngineeringPlanView(value: unknown): value is EngineeringPlanViewDto {
  return (
    typeof value === 'object' &&
    value !== null &&
    'overview' in value &&
    'phases' in value &&
    typeof (value as EngineeringPlanViewDto).overview?.goal === 'string'
  )
}

export function isCanonicalEngineeringPlan(value: unknown): value is EngineeringPlanDto {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.plan_id === 'string' &&
    typeof candidate.requirements === 'object' &&
    candidate.requirements !== null &&
    !Array.isArray(candidate.requirements) &&
    typeof candidate.root_goal === 'object' &&
    candidate.root_goal !== null
  )
}

type CanonicalEngineeringPlanPanelProps = {
  plan: EngineeringPlanDto
}

export function CanonicalEngineeringPlanPanel({ plan }: CanonicalEngineeringPlanPanelProps) {
  const requirementCount = Object.keys(plan.requirements ?? {}).length
  const traversal = plan.traversal as PlannerTraversalStateDto | undefined

  return (
    <div className="inspector-engineering-plan">
      <section className="inspector-workflow-status__section">
        <h3 className="inspector-workflow-status__title">Engineering plan (canonical)</h3>
        <dl className="inspector-status-grid">
          <div>
            <dt>Plan id</dt>
            <dd>{plan.plan_id}</dd>
          </div>
          <div>
            <dt>Workflow</dt>
            <dd>{plan.workflow_id}</dd>
          </div>
          <div>
            <dt>Requirements</dt>
            <dd>{requirementCount}</dd>
          </div>
          <div>
            <dt>Phases</dt>
            <dd>{plan.phases?.length ?? 0}</dd>
          </div>
          {plan.input_strategy?.current_phase ? (
            <div>
              <dt>Current phase</dt>
              <dd>{plan.input_strategy.current_phase}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      {traversal ? <PlannerTraversalPanel traversal={traversal} /> : null}

      <details className="inspector-rationale-details">
        <summary>Full canonical plan JSON</summary>
        <pre className="inspector-code">{JSON.stringify(plan, null, 2)}</pre>
      </details>
    </div>
  )
}
