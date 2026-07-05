import { useEffect, useMemo, useState } from 'react'

import { DevNodeHoverSurface } from '@dev-ui/DevNodeHoverSurface'
import { useTaskStore } from '@/store/taskStore'

import type { NodeProvenanceDto } from '@/types/backend/api'
import type { ParameterDefinitionDto } from '@/types/backend/parameters'
import { DEFAULT_WORKFLOW_ASK_PROMPT } from './workflowAsk'
import type { WorkflowAsk } from './workflowAsk'
import { ComposerInlineInput } from './ComposerInlineInput'
import { MaterialSearchInput } from './MaterialSearchInput'

import './ComposerInlineInput.css'
import './ComposerInput.css'
import './WorkflowPanel.css'

interface WorkflowComposerProps {
  ask: WorkflowAsk
  disabled?: boolean
  fallbackProvenance?: NodeProvenanceDto | null
}

function initialValue(parameter: ParameterDefinitionDto): unknown {
  if (parameter.value != null) {
    return parameter.value
  }
  if (parameter.default_value != null) {
    return parameter.default_value
  }
  if (parameter.type === 'checkbox') {
    return false
  }
  if (parameter.type === 'multi_select') {
    return []
  }
  return ''
}

function initialUnit(parameter: ParameterDefinitionDto): string {
  return parameter.default_unit || parameter.units[0] || 'dimensionless'
}

function composerPlaceholder(parameter: ParameterDefinitionDto): string {
  if (parameter.type === 'material') {
    return 'Start typing to search materials…'
  }

  if (parameter.type === 'checkbox') {
    return `Confirm ${parameter.label.toLowerCase()}.`
  }

  return `Enter ${parameter.label.toLowerCase()}…`
}

function usesComposerUnitPills(parameter: ParameterDefinitionDto): boolean {
  return parameter.units.length > 0
}

function usesInlineComposerRow(parameter: ParameterDefinitionDto | null): boolean {
  if (!parameter) {
    return false
  }

  return (
    parameter.type === 'text' ||
    parameter.type === 'number' ||
    parameter.type === 'unit' ||
    parameter.type === 'material'
  )
}

function askHeading(ask: WorkflowAsk): string | null {
  if (!ask.prompt) {
    return null
  }

  switch (ask.kind) {
    case 'input':
      return 'Ask:'
    case 'clarify':
      return 'Blocked:'
    case 'waiting':
      return 'Status:'
    default:
      return null
  }
}

function renderInlineComposerInput({
  parameter,
  textValue,
  unit,
  setValue,
  setUnit,
  busy,
  submitting,
  canSubmit,
  submitCurrentValue,
}: {
  parameter: ParameterDefinitionDto
  textValue: string
  unit: string
  setValue: (value: unknown) => void
  setUnit: (unit: string) => void
  busy: boolean
  submitting: boolean
  canSubmit: boolean
  submitCurrentValue: (nextValue?: unknown, displayValue?: string) => Promise<void>
}) {
  if (parameter.type === 'material') {
    return (
      <MaterialSearchInput
        inline
        value={textValue}
        onChange={setValue}
        onSubmit={(nextValue, displayValue) => void submitCurrentValue(nextValue, displayValue)}
        disabled={busy}
        submitting={submitting}
        placeholder={composerPlaceholder(parameter)}
      />
    )
  }

  const showUnits = usesComposerUnitPills(parameter)

  return (
    <ComposerInlineInput
      key={parameter.name}
      value={textValue}
      onChange={(next) => setValue(next)}
      placeholder="Value…"
      disabled={busy}
      submitting={submitting}
      canSubmit={canSubmit}
      onSubmit={() => void submitCurrentValue()}
      inputMode={parameter.type === 'text' ? 'text' : 'decimal'}
      variant={parameter.type === 'text' ? 'text' : 'numeric'}
      units={showUnits ? parameter.units : undefined}
      unit={showUnits ? unit : undefined}
      onUnitChange={showUnits ? setUnit : undefined}
      unitAriaLabel={showUnits ? `${parameter.label} unit` : undefined}
      focusKey={parameter.name}
    />
  )
}

export function WorkflowComposer({
  ask,
  disabled,
  fallbackProvenance,
}: WorkflowComposerProps) {
  const submitParameter = useTaskStore((state) => state.submitParameter)
  const parameter = ask.parameter

  const [value, setValue] = useState<unknown>(() => (parameter ? initialValue(parameter) : ''))
  const [unit, setUnit] = useState(() => (parameter ? initialUnit(parameter) : 'dimensionless'))
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setSubmitting(false)
    if (!parameter) {
      setValue('')
      setUnit('dimensionless')
      return
    }
    setValue(initialValue(parameter))
    setUnit(initialUnit(parameter))
  }, [parameter])

  const busy = Boolean(disabled || submitting)
  const options = useMemo(() => parameter?.options ?? [], [parameter])
  const askPrompt = ask.prompt
  const heading = askHeading(ask)

  const submitCurrentValue = async (nextValue?: unknown, displayValue?: string) => {
    if (!parameter || busy) {
      return
    }

    const resolvedValue = nextValue !== undefined ? nextValue : value
    setSubmitting(true)
    try {
      let payload: unknown = resolvedValue
      if (parameter.type === 'number' || parameter.type === 'unit') {
        payload = resolvedValue === '' ? null : Number(resolvedValue)
      }

      await submitParameter(
        parameter.name,
        payload,
        parameter.units.length > 0 ? unit : undefined,
        displayValue,
      )
      setValue(parameter.type === 'multi_select' ? [] : '')
    } finally {
      setSubmitting(false)
    }
  }

  const canSubmit =
    parameter != null &&
    !busy &&
    (parameter.type === 'checkbox' ||
      parameter.type === 'dropdown' ||
      (parameter.type === 'multi_select'
        ? Array.isArray(value) && value.length > 0
        : value !== '' && value != null))

  const textValue = value == null ? '' : String(value)
  const inlineComposerRow = usesInlineComposerRow(parameter)
  const composerProvenance = parameter?.provenance ?? fallbackProvenance ?? null
  const showAskBlock = Boolean(askPrompt || inlineComposerRow)

  return (
    <div className="workflow-panel__composer">
      {parameter?.editing ? (
        <p className="workflow-panel__edit-notice">
          Editing this input. Downstream values were cleared; submit to continue the workflow.
        </p>
      ) : null}
      {showAskBlock ? (
        <div className="workflow-panel__next-step">
          {heading ? (
            <p className="workflow-panel__next-step-heading">
              <strong>{heading}</strong>
            </p>
          ) : null}
          {inlineComposerRow && parameter && ask.kind === 'input' ? (
            <div className="workflow-panel__next-step-inline">
              {askPrompt ? (
                <DevNodeHoverSurface provenance={composerProvenance} fallbackProvenance={fallbackProvenance}>
                  <span className="workflow-panel__next-step-text">{askPrompt}</span>
                </DevNodeHoverSurface>
              ) : null}
              {renderInlineComposerInput({
                parameter,
                textValue,
                unit,
                setValue,
                setUnit,
                busy,
                submitting,
                canSubmit,
                submitCurrentValue,
              })}
            </div>
          ) : askPrompt ? (
            <DevNodeHoverSurface provenance={composerProvenance} fallbackProvenance={fallbackProvenance}>
              <span
                className={`workflow-panel__next-step-text${
                  ask.kind === 'clarify' ? ' workflow-panel__next-step-text--blocked' : ''
                }`}
              >
                {askPrompt}
              </span>
            </DevNodeHoverSurface>
          ) : null}
        </div>
      ) : null}

      {parameter &&
      ask.kind === 'input' &&
      (parameter.type === 'dropdown' || parameter.type === 'multi_select') &&
      options.length > 0 ? (
        <div className="workflow-panel__options" role="listbox" aria-label={`${parameter.label} options`}>
          {options.map((option) => {
            const selected =
              parameter.type === 'multi_select'
                ? Array.isArray(value) && value.includes(option.value)
                : value === option.value

            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={selected}
                className={`workflow-panel__option${selected ? ' workflow-panel__option--selected' : ''}`}
                disabled={busy}
                onClick={() => {
                  if (parameter.type === 'dropdown') {
                    setValue(option.value)
                    void submitCurrentValue(option.value)
                    return
                  }

                  const current = Array.isArray(value) ? value.map(String) : []
                  const next = current.includes(option.value)
                    ? current.filter((entry) => entry !== option.value)
                    : [...current, option.value]
                  setValue(next)
                }}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      ) : null}

      {parameter?.type === 'checkbox' && ask.kind === 'input' ? (
        <div className="workflow-panel__checkbox-row">
          <button
            type="button"
            className={`workflow-panel__option${value === true ? ' workflow-panel__option--selected' : ''}`}
            disabled={busy}
            onClick={() => void submitCurrentValue(true)}
          >
            Yes
          </button>
          <button
            type="button"
            className={`workflow-panel__option${value === false ? ' workflow-panel__option--selected' : ''}`}
            disabled={busy}
            onClick={() => void submitCurrentValue(false)}
          >
            No
          </button>
        </div>
      ) : null}

      {parameter?.type === 'multi_select' && ask.kind === 'input' ? (
        <div className="workflow-panel__multi-actions">
          <button
            type="button"
            className="workflow-panel__submit workflow-panel__submit--inline"
            disabled={!canSubmit}
            onClick={() => void submitCurrentValue()}
          >
            {submitting ? 'Submitting…' : 'Submit selection'}
          </button>
        </div>
      ) : null}

      {ask.kind === 'none' && !parameter ? (
        <p className="workflow-panel__empty">{DEFAULT_WORKFLOW_ASK_PROMPT}</p>
      ) : null}
    </div>
  )
}
